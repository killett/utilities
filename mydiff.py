from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import emmykit as ek

__version__: str = "0.1.0"


class Options:
    """Class that has all global options in one place."""

    def __init__(self) -> None:
        """Initialize the Options class with default values."""
        # The invoked name of this script, without the .py extension.
        self.my_name: str = Path(sys.argv[0]).stem
        # Use the -debug command line argument to change to DEBUG.
        self.log_mode: int = logging.INFO
        self.args: argparse.Namespace = argparse.Namespace()
        # Default to the current working directory.
        self.default_dir: Path = Path.cwd().expanduser().resolve(strict=True)


def parse_arguments(options: Options) -> None:
    """Parse command-line arguments.

    Args:
        options: Options object whose ``args`` and ``log_mode`` are updated in place.

    Returns:
        None, but updates options.args with parsed arguments.

    Raises:
        SystemExit: If the '-v'/'--version' flag is provided (prints and exits).
    """
    parser = argparse.ArgumentParser(description="Diff two files using ek.my_diff().")
    parser.add_argument("orig_path", type=Path, help="Path to original file.")
    parser.add_argument("changed_path", type=Path, help="Path to changed file.")
    parser.add_argument(
        "--diff_choice",
        type=int,
        default=1,
        help="0 = old-style diff, 1 = unified diff with 0 context lines, "
        "2+ = unified diff with 'diff_choice - 1' context lines",
    )
    parser.add_argument(
        "--changed_color",
        type=str,
        default=ek.ANSI_CYAN,
        help="Color for unchanged characters in changed lines (default: ANSI_CYAN)",
    )
    parser.add_argument(
        "--deleted_color",
        type=str,
        default=ek.ANSI_RED,
        help="Color for deleted characters in original lines (default: ANSI_RED)",
    )
    parser.add_argument(
        "--added_color",
        type=str,
        default=ek.ANSI_GREEN,
        help="Color for added characters in changed lines (default: ANSI_GREEN)",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-debug", "--debug", action="store_true", help="Enable DEBUG logging."
    )
    options.args = parser.parse_args()
    if options.args.debug:
        options.log_mode = logging.DEBUG


def main() -> None:
    """Read both files and print their diff."""
    options: Options = Options()
    parse_arguments(options)
    memory_handler = ek.configure_logging(
        options.my_name, log_level=options.log_mode, rawlog=True
    )
    orig_text = ek.my_fopen(options.args.orig_path)
    changed_text = ek.my_fopen(options.args.changed_path)
    # ek.my_fopen() signals failure with None, so testing for False never fired.
    if orig_text is None:
        logging.error(
            f"Failed to read original file: {os.fspath(options.args.orig_path)}"
        )
        return
    if changed_text is None:
        logging.error(
            f"Failed to read changed file: {os.fspath(options.args.changed_path)}"
        )
        return
    if orig_text == changed_text:
        return  # Standard diff would show no changes
    ek.my_diff(
        orig_text,
        changed_text,
        options.args.orig_path,
        changed_path=options.args.changed_path,
        diff_choice=options.args.diff_choice,
        changed_color=options.args.changed_color,
        deleted_color=options.args.deleted_color,
        added_color=options.args.added_color,
    )
    if memory_handler is not None:
        ek.print_all_errors(memory_handler)
    logging.shutdown()


if __name__ == "__main__":
    main()
