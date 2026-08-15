"""Tests for myaudit.py."""

from __future__ import annotations

import myaudit


def test_missing_lint_tooling_names_only_the_absent_modules() -> None:
    probed = ("sys", "no_such_module_xyz", "os")

    assert myaudit.missing_lint_tooling(probed) == ["no_such_module_xyz"]


def test_missing_lint_tooling_returns_empty_when_everything_is_importable() -> None:
    assert myaudit.missing_lint_tooling(("sys", "os", "json")) == []


def test_missing_lint_tooling_preserves_probe_order() -> None:
    probed = ("no_such_a", "os", "no_such_b")

    assert myaudit.missing_lint_tooling(probed) == ["no_such_a", "no_such_b"]
