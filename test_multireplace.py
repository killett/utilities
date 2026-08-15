"""Tests for multireplace.py."""

from __future__ import annotations

import sys
from pathlib import Path

import multireplace
import pytest


def test_glob_pattern_defaults_to_everything(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # ek.multireplace() runs the glob through _validate_glob_pattern() and
    # sys.exit(2)s on a bad one, so a None default would kill every plain run.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["multireplace.py", "old", "new"])
    options = multireplace.Options()

    multireplace.parse_arguments(options)

    assert options.args.glob_pattern == "*"
    assert options.args.dir == tmp_path.resolve()
    assert options.args.recursive is False


def test_positional_glob_and_dir_flag_are_honoured(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["multireplace.py", "old", "new", "*.py", "--dir", str(tmp_path), "-r"],
    )
    options = multireplace.Options()

    multireplace.parse_arguments(options)

    assert options.args.old_str == "old"
    assert options.args.new_str == "new"
    assert options.args.glob_pattern == "*.py"
    assert options.args.dir == tmp_path
    assert options.args.recursive is True
