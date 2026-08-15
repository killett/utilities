from __future__ import annotations

import argparse
import io
import logging
import os
import re
import sys
import tokenize
from collections.abc import Iterable
from pathlib import Path

import emmykit as ek

__version__: str = "0.1.1"


class Options:
    """Class that has all global options in one place."""

    def __init__(self) -> None:
        """Initialize the Options class with default values."""
        # The invoked name of this script, without the .py extension.
        self.my_name: str = Path(sys.argv[0]).stem
        self.default_exclude_dirs: set[str] = set(ek.DEFAULT_EXCLUDE_DIRS)
        # Use the -debug command line argument to change to DEBUG.
        self.log_mode: int = logging.INFO
        self.args: argparse.Namespace = argparse.Namespace()


def parse_arguments(options: Options) -> None:
    """Parse command-line arguments.

    Args:
        options: Options object whose ``args`` and ``log_mode`` are updated in place.

    Returns:
        None, but updates options.args with parsed arguments.

    Raises:
        SystemExit: If the '-v'/'--version' flag is provided (prints and exits).
    """
    parser = argparse.ArgumentParser(
        description="Search Python files and print full logical statements that match a pattern."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,  # parse as Path at the boundary
        help="Files and/or directories to search.",
    )
    parser.add_argument(
        "-p", "--pattern", required=True, help="Search pattern (string or regex)."
    )
    parser.add_argument(
        "-E",
        "--regex",
        action="store_true",
        help="Treat the pattern as a regular expression.",
    )
    parser.add_argument(
        "-i", "--ignore-case", action="store_true", help="Case-insensitive match."
    )
    parser.add_argument(
        "-n",
        "--line-numbers",
        action="store_true",
        help="Show line numbers in output blocks.",
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Recurse into directories."
    )
    parser.add_argument(
        "--no-glob",
        action="store_true",
        help="Do not automatically filter for *.py inside directories.",
    )
    parser.add_argument(
        "--exclude-dirs",
        action="extend",
        nargs="+",
        default=None,
        help=f"Directory name to exclude (can be given multiple times). Any directories given will be added to the default set: {sorted(options.default_exclude_dirs)}",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-debug", "--debug", action="store_true", help="Enable debug logging."
    )
    options.args = parser.parse_args()
    options.args.exclude_dirs = set(ek.DEFAULT_EXCLUDE_DIRS) | set(
        options.args.exclude_dirs or []
    )
    if options.args.debug:
        options.log_mode = logging.DEBUG


def _is_excluded(path: Path, excluded: set[str]) -> bool:
    """Return True if any ancestor directory name is in the excluded set."""
    # Only compare directory names (Path.name); do not do string-prefix checks.
    return any(parent.name in excluded for parent in path.parents)


def iter_files(
    paths: Iterable[str | os.PathLike[str]],
    recursive: bool,
    excluded: set[str],
    only_py: bool,
) -> Iterable[Path]:
    """Yield files from given paths, respecting recursion and directory excludes.

    Parameters that represent paths accept str | os.PathLike[str] at the boundary.
    Returned paths are pathlib.Path instances.

    Args:
        paths:     Files and/or directories to walk.
        recursive: Whether to recurse into subdirectories.
        excluded:  Directory names whose contents are skipped.
        only_py:   Whether to restrict matches to ``*.py``.

    Yields:
        Each matching file as a pathlib.Path.
    """
    pattern = "*.py" if only_py else "*"

    for raw in paths:
        base = Path(raw)

        if ek.safe_is_dir(base):
            if recursive:
                # Prefer Path.rglob for recursion (portable across 3.9+).
                for f in base.rglob(pattern):
                    if ek.safe_is_file(f) and not _is_excluded(f, excluded):
                        yield f
            else:
                for f in base.glob(pattern):
                    if ek.safe_is_file(f) and not _is_excluded(f, excluded):
                        yield f
        else:
            # Single file (or non-existent); yield if it meets filters.
            if (
                ek.safe_is_file(base)
                and (not only_py or base.suffix == ".py")
                and not _is_excluded(base, excluded)
            ):
                yield base


def _statement_spans(src: str) -> list[tuple[int, int]]:
    """Return list of (start_line, end_line) for each logical statement in the source."""
    reader = io.StringIO(src).readline
    spans: list[tuple[int, int]] = []
    depth = 0
    start_line: int | None = None

    for tok in tokenize.generate_tokens(reader):
        tok_type, tok_str, start, end, _ = tok

        # establish start at first meaningful token of a statement
        if start_line is None and tok_type not in (
            tokenize.NL,
            tokenize.COMMENT,
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.ENDMARKER,
        ):
            start_line = start[0]

        if tok_type == tokenize.OP:
            if tok_str in "([{":
                depth += 1
            elif tok_str in ")]}":
                depth -= 1
            elif tok_str == ";" and depth == 0 and start_line is not None:
                spans.append((start_line, start[0]))
                start_line = None
                continue

        if tok_type == tokenize.NEWLINE and depth == 0:
            if start_line is not None:
                spans.append((start_line, end[0]))
            start_line = None

        if tok_type == tokenize.ENDMARKER:
            break

    return spans


def _mask_strings_and_comments(src: str) -> str:
    """Return source with STRING and COMMENT contents replaced by spaces (preserving positions)."""
    lines = src.splitlines(keepends=True)
    matrix = [list(line) for line in lines]
    reader = io.StringIO(src).readline
    for tok in tokenize.generate_tokens(reader):
        tok_type, _tok_str, start, end, _ = tok
        if tok_type in (tokenize.STRING, tokenize.COMMENT):
            (sr, sc), (er, ec) = start, end
            # mask all full lines covered by the token
            for r in range(sr - 1, er - 1):
                cstart = sc if r == sr - 1 else 0
                for c in range(cstart, len(matrix[r])):
                    if matrix[r][c] != "\n":
                        matrix[r][c] = " "
            # final line (partial)
            r = er - 1
            if 0 <= r < len(matrix):
                cstart = 0 if sr != er else sc
                for c in range(cstart, ec):
                    if matrix[r][c] != "\n":
                        matrix[r][c] = " "
    return "".join("".join(row) for row in matrix)


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or adjacent spans."""
    if not spans:
        return []
    spans = sorted(spans)
    merged: list[list[int]] = [[spans[0][0], spans[0][1]]]
    for s, e in spans[1:]:
        last = merged[-1]
        if s <= last[1] + 1:
            last[1] = max(last[1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def _extract_blocks(
    src: str, spans: list[tuple[int, int]], show_line_numbers: bool
) -> list[str]:
    """Return pretty-printed blocks for each span."""
    lines = src.splitlines()
    width = 0
    if show_line_numbers:
        max_line = max((e for _, e in spans), default=0)
        width = len(str(max_line))
    blocks: list[str] = []
    for s, e in spans:
        segment = lines[s - 1 : e]
        if show_line_numbers:
            segment = [
                f"{i:>{width}} | {line}"
                for i, line in zip(range(s, e + 1), segment, strict=False)
            ]
        blocks.append("\n".join(segment))
    return blocks


def search_file(
    path: str | os.PathLike[str],
    pattern: str,
    *,
    regex: bool,
    ignore_case: bool,
    show_line_numbers: bool,
) -> list[str]:
    """Return matching blocks for a single file.

    Args:
        path:              The Python file to search.
        pattern:           Literal text, or a regular expression when ``regex`` is True.
        regex:             Whether ``pattern`` is a regular expression.
        ignore_case:       Whether to match case-insensitively.
        show_line_numbers: Whether to prefix each output line with its line number.

    Returns:
        One string per matching logical statement, in source order.
    """
    p = ek.ensure_file(path)
    text = ek.my_fopen(p, suppress_errors=True)
    if not isinstance(text, str):
        logging.warning("Skipping %s (unreadable or non-text).", os.fspath(p))
        return []

    masked = _mask_strings_and_comments(text)
    flags = re.IGNORECASE if ignore_case else 0
    pat = re.compile(pattern if regex else re.escape(pattern), flags)

    # lines that contain a match (in code, not in strings/comments)
    hit_lines: set[int] = set()
    for m in pat.finditer(masked):
        before = masked[: m.start()]
        line = before.count("\n") + 1
        hit_lines.add(line)

    if not hit_lines:
        return []

    # map lines to statement spans
    spans = _statement_spans(text)
    line_to_span: dict[int, tuple[int, int]] = {}
    for s, e in spans:
        for ln in range(s, e + 1):
            line_to_span[ln] = (s, e)

    chosen: list[tuple[int, int]] = []
    for ln in sorted(hit_lines):
        sp = line_to_span.get(ln)
        if sp:
            chosen.append(sp)

    chosen = _merge_spans(chosen)
    return _extract_blocks(text, chosen, show_line_numbers)


def main() -> None:
    """Search the requested paths and print every matching logical statement."""
    options: Options = Options()
    parse_arguments(options)
    logging.basicConfig(
        level=options.log_mode,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    any_hits = False

    for file in iter_files(
        options.args.paths,
        options.args.recursive,
        options.args.exclude_dirs,
        only_py=not options.args.no_glob,
    ):
        results = search_file(
            file,
            options.args.pattern,
            regex=options.args.regex,
            ignore_case=options.args.ignore_case,
            show_line_numbers=options.args.line_numbers,
        )
        if results:
            any_hits = True
            print(f"# {os.fspath(file)}")
            for block in results:
                print(block)
                print()  # extra newline between blocks

    if not any_hits:
        logging.info("No matches found.")

    logging.shutdown()


if __name__ == "__main__":
    main()
