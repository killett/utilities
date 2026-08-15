"""Tests for mydiff.py."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import emmykit as ek
import pytest

import mydiff

# One recorded ek.my_diff() call: its positional args and its keyword args.
DiffCalls = list[tuple[tuple[Any, ...], dict[str, Any]]]


@pytest.fixture(autouse=True)
def _isolate_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep mydiff.main() away from the global logging setup.

    ek.configure_logging() creates a ./logs directory and replaces the root
    logger's handlers, and logging.shutdown() closes them. Both would break
    pytest's own capture for this and every later test, and neither is what
    these tests are about.
    """
    monkeypatch.setattr(ek, "configure_logging", lambda *args, **kwargs: None)
    monkeypatch.setattr(logging, "shutdown", lambda *args, **kwargs: None)


@pytest.fixture
def my_diff_calls(monkeypatch: pytest.MonkeyPatch) -> DiffCalls:
    """Replace ek.my_diff with a recorder and return the list of (args, kwargs)."""
    calls: DiffCalls = []
    monkeypatch.setattr(
        ek, "my_diff", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    return calls


def test_unreadable_original_reports_the_error_and_never_diffs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    my_diff_calls: DiffCalls,
) -> None:
    # ek.my_fopen() returns None on failure, so the original `is False` guard
    # never fired and None was handed straight to ek.my_diff().
    missing = tmp_path / "gone.txt"
    present = tmp_path / "there.txt"
    present.write_text("alpha\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["mydiff.py", str(missing), str(present)])

    with caplog.at_level(logging.ERROR):
        mydiff.main()

    assert my_diff_calls == []
    assert f"Failed to read original file: {missing}" in caplog.text


def test_unreadable_changed_file_reports_the_error_and_never_diffs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    my_diff_calls: DiffCalls,
) -> None:
    present = tmp_path / "there.txt"
    present.write_text("alpha\n", encoding="utf-8")
    missing = tmp_path / "gone.txt"
    monkeypatch.setattr(sys, "argv", ["mydiff.py", str(present), str(missing)])

    with caplog.at_level(logging.ERROR):
        mydiff.main()

    assert my_diff_calls == []
    assert f"Failed to read changed file: {missing}" in caplog.text


def test_identical_files_are_not_diffed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, my_diff_calls: DiffCalls
) -> None:
    same = tmp_path / "same.txt"
    same.write_text("alpha\nbeta\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["mydiff.py", str(same), str(same)])

    mydiff.main()

    assert my_diff_calls == []


def test_differing_files_are_passed_to_my_diff_with_their_contents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, my_diff_calls: DiffCalls
) -> None:
    orig = tmp_path / "a.txt"
    changed = tmp_path / "b.txt"
    orig.write_text("alpha\n", encoding="utf-8")
    changed.write_text("beta\n", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["mydiff.py", str(orig), str(changed), "--diff_choice", "3"]
    )

    mydiff.main()

    assert len(my_diff_calls) == 1
    args, kwargs = my_diff_calls[0]
    assert args[0] == "alpha\n"
    assert args[1] == "beta\n"
    assert kwargs["changed_path"] == changed
    assert kwargs["diff_choice"] == 3
