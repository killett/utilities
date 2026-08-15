"""Tests for treeview.py."""

from __future__ import annotations

import sys
from pathlib import Path

import emmykit as ek
import pytest

import treeview


def test_user_excludes_are_added_to_the_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys, "argv", ["treeview.py", ".", "--exclude-dirs", "myextra", "another"]
    )
    options = treeview.Options()

    treeview.parse_arguments(options)

    assert options.args.exclude_dirs >= set(ek.DEFAULT_EXCLUDE_DIRS)
    assert {"myextra", "another"} <= options.args.exclude_dirs


def test_without_user_excludes_the_defaults_are_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["treeview.py", "."])
    options = treeview.Options()

    treeview.parse_arguments(options)

    assert options.args.exclude_dirs == set(ek.DEFAULT_EXCLUDE_DIRS)


def test_directory_defaults_to_the_current_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["treeview.py"])
    options = treeview.Options()

    treeview.parse_arguments(options)

    assert options.args.directory == tmp_path.resolve()
