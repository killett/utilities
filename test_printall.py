"""Tests for printall.py."""

from __future__ import annotations

import sys
from pathlib import Path

import emmykit as ek
import printall
import pytest

MULTILINE_CALL = """import logging

TARGET = "needle_value in a string"
# needle_value in a comment


def wide_call() -> None:
    logging.info(
        "hello %s",
        needle_value,
    )


needle_value = 42
"""


def test_mask_preserves_layout_and_hides_string_and_comment_text() -> None:
    src = 'x = "needle"  # needle\ny = 1\n'
    masked = printall._mask_strings_and_comments(src)

    # 'x = ' survives; the 8-char string, the 2 separating spaces and the
    # 8-char comment all become spaces, so line 1 stays 22 characters wide.
    assert masked.splitlines() == ["x = " + " " * 18, "y = 1"]
    assert len(masked) == len(src)
    assert "needle" not in masked


def test_statement_spans_keeps_a_bracketed_call_as_one_statement() -> None:
    spans = printall._statement_spans(MULTILINE_CALL)

    # logging.info( ... ) occupies lines 8-11 of MULTILINE_CALL. Only the
    # closing NEWLINE ends a statement; the NL tokens at the end of lines
    # 8, 9 and 10 must not split it into four one-line spans.
    assert (8, 11) in spans
    assert not any(start == end for start, end in spans if 8 <= start <= 11)


def test_statement_spans_splits_on_semicolons() -> None:
    assert printall._statement_spans("a = 1; b = 2\n") == [(1, 1), (1, 1)]


def test_merge_spans_merges_overlapping_and_adjacent_but_not_gapped() -> None:
    assert printall._merge_spans([(1, 3), (4, 5), (8, 9)]) == [(1, 5), (8, 9)]


def test_merge_spans_on_empty_input() -> None:
    assert printall._merge_spans([]) == []


def test_extract_blocks_pads_line_numbers_to_the_widest_line() -> None:
    src = "\n".join(f"line{i}" for i in range(1, 11)) + "\n"

    blocks = printall._extract_blocks(src, [(9, 10)], show_line_numbers=True)

    assert blocks == [" 9 | line9\n10 | line10"]


def test_extract_blocks_without_line_numbers_returns_raw_source() -> None:
    src = "alpha\nbeta\ngamma\n"

    assert printall._extract_blocks(src, [(2, 3)], show_line_numbers=False) == [
        "beta\ngamma"
    ]


def test_is_excluded_matches_directory_names_not_substrings(tmp_path: Path) -> None:
    excluded = {"build"}

    assert printall._is_excluded(tmp_path / "build" / "f.py", excluded) is True
    assert printall._is_excluded(tmp_path / "buildings" / "f.py", excluded) is False


def _make_tree(root: Path) -> None:
    (root / "top.py").write_text("a = 1\n", encoding="utf-8")
    (root / "top.txt").write_text("not python\n", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "nested.py").write_text("b = 2\n", encoding="utf-8")
    (root / "skipme").mkdir()
    (root / "skipme" / "hidden.py").write_text("c = 3\n", encoding="utf-8")


def test_iter_files_non_recursive_stays_at_the_top_level(tmp_path: Path) -> None:
    _make_tree(tmp_path)

    found = sorted(
        p.name
        for p in printall.iter_files(
            [tmp_path], recursive=False, excluded=set(), only_py=True
        )
    )

    assert found == ["top.py"]


def test_iter_files_recursive_descends_and_honours_excludes(tmp_path: Path) -> None:
    _make_tree(tmp_path)

    found = sorted(
        p.name
        for p in printall.iter_files(
            [tmp_path], recursive=True, excluded={"skipme"}, only_py=True
        )
    )

    assert found == ["nested.py", "top.py"]


def test_iter_files_without_only_py_yields_non_python_files(tmp_path: Path) -> None:
    _make_tree(tmp_path)

    found = sorted(
        p.name
        for p in printall.iter_files(
            [tmp_path], recursive=False, excluded=set(), only_py=False
        )
    )

    assert found == ["top.py", "top.txt"]


def test_iter_files_named_file_is_filtered_by_suffix(tmp_path: Path) -> None:
    _make_tree(tmp_path)

    assert (
        list(
            printall.iter_files(
                [tmp_path / "top.txt"], recursive=False, excluded=set(), only_py=True
            )
        )
        == []
    )
    assert [
        p.name
        for p in printall.iter_files(
            [tmp_path / "top.txt"], recursive=False, excluded=set(), only_py=False
        )
    ] == ["top.txt"]


def test_search_file_returns_whole_statement_and_ignores_strings_and_comments(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample.py"
    target.write_text(MULTILINE_CALL, encoding="utf-8")

    blocks = printall.search_file(
        target, "needle_value", regex=False, ignore_case=False, show_line_numbers=False
    )

    assert blocks == [
        '    logging.info(\n        "hello %s",\n        needle_value,\n    )',
        "needle_value = 42",
    ]


def test_search_file_treats_a_plain_pattern_literally(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("abc = 1\n", encoding="utf-8")

    assert (
        printall.search_file(
            target, "a.c", regex=False, ignore_case=False, show_line_numbers=False
        )
        == []
    )
    assert printall.search_file(
        target, "a.c", regex=True, ignore_case=False, show_line_numbers=False
    ) == ["abc = 1"]


def test_search_file_ignore_case(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("needle = 1\n", encoding="utf-8")

    assert (
        printall.search_file(
            target, "NEEDLE", regex=False, ignore_case=False, show_line_numbers=False
        )
        == []
    )
    assert printall.search_file(
        target, "NEEDLE", regex=False, ignore_case=True, show_line_numbers=False
    ) == ["needle = 1"]


def test_parse_arguments_adds_user_excludes_to_the_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["printall.py", ".", "-p", "x", "--exclude-dirs", "myextra"]
    )
    options = printall.Options()

    printall.parse_arguments(options)

    assert options.args.exclude_dirs >= set(ek.DEFAULT_EXCLUDE_DIRS)
    assert "myextra" in options.args.exclude_dirs


def test_parse_arguments_requires_a_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["printall.py", "."])

    with pytest.raises(SystemExit) as excinfo:
        printall.parse_arguments(printall.Options())

    assert excinfo.value.code == 2
