"""Tests for detect_country.py."""

from __future__ import annotations

import re

import emmykit as ek
import pytest

import detect_country

# detect_country.main() calls logging.basicConfig(force=True), which removes
# pytest's caplog handler -- caplog captures 0 records after it runs. These
# tests assert on capfd (the real stderr) instead. Swapping capfd for caplog
# here produces an assertion against an empty string that silently passes.

LOG_LINE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - INFO - Detected country: NL$"
)


def test_detect_country_is_called_without_forcing_wtfismyip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # force_wtfismyip=True switches to a different provider with different
    # availability and rate limits. The False was deliberate; nothing else
    # records it. Asserting the whole kwargs dict also catches the argument
    # being passed positionally or renamed.
    calls: list[dict[str, object]] = []

    def _record(**kwargs: object) -> str:
        calls.append(kwargs)
        return "NL"

    monkeypatch.setattr(ek, "detect_country", _record)

    detect_country.main()

    assert calls == [{"force_wtfismyip": False}]


def test_detected_country_reaches_the_output(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    # Catches logging a stale variable or the wrong f-string field -- the
    # script's entire purpose, silently absent.
    monkeypatch.setattr(ek, "detect_country", lambda **kw: "Aotearoa")

    detect_country.main()

    assert "Detected country: Aotearoa" in capfd.readouterr().err


def test_log_line_keeps_its_configured_format(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    # Regression test for the force=True in basicConfig. emmykit installs a
    # root handler at import time, so without force=True basicConfig is a
    # documented no-op: the timestamp and level prefix vanish and -debug goes
    # inert across the repo. That bug shipped in four scripts once already.
    monkeypatch.setattr(ek, "detect_country", lambda **kw: "NL")

    detect_country.main()

    err = capfd.readouterr().err.strip()
    assert LOG_LINE.match(err), f"log line lost its configured format: {err!r}"
