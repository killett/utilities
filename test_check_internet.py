"""Tests for check_internet.py."""

from __future__ import annotations

import logging
import sys
from typing import Any

import emmykit as ek
import pytest

import check_internet

# parse_arguments() runs BEFORE main() calls logging.basicConfig(force=True),
# so caplog still works for the warnings it emits. Anything driving main()
# must use capfd instead: basicConfig(force=True) removes pytest's caplog
# handler, after which caplog captures 0 records and any assertion on it
# passes vacuously.


def _parse(monkeypatch: pytest.MonkeyPatch, *argv: str) -> check_internet.Options:
    """Run parse_arguments() with the given CLI arguments, return the Options."""
    monkeypatch.setattr(sys, "argv", ["check_internet.py", *argv])
    options = check_internet.Options()
    check_internet.parse_arguments(options)
    return options


def _run_main(
    monkeypatch: pytest.MonkeyPatch, online: bool, *argv: str
) -> tuple[list[dict[str, Any]], int | str | None]:
    """Drive main() with a stubbed connectivity check.

    Returns the kwargs ek.is_internet_available was called with, and the
    SystemExit code -- or None when main() returned without exiting.
    """
    calls: list[dict[str, Any]] = []

    def _stub(**kwargs: Any) -> bool:
        calls.append(kwargs)
        return online

    monkeypatch.setattr(ek, "is_internet_available", _stub)
    monkeypatch.setattr(sys, "argv", ["check_internet.py", *argv])
    try:
        check_internet.main()
    except SystemExit as exc:
        return calls, exc.code
    return calls, None


def test_timeout_below_minimum_is_clamped_and_warned(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Catches min() where max() belongs, or clamping to the wrong bound.
    # 0.5 is Options.min_timeout, the documented floor.
    with caplog.at_level(logging.WARNING):
        options = _parse(monkeypatch, "-t", "0.1")

    assert options.timeout_per_step == 0.5
    assert "requested timeout < minimum (0.5); bumping to 0.5s" in caplog.text


def test_timeout_above_minimum_is_untouched_and_silent(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Without this, an implementation that always returned min_timeout would
    # still pass the test above.
    with caplog.at_level(logging.WARNING):
        options = _parse(monkeypatch, "-t", "10")

    assert options.timeout_per_step == 10.0
    assert caplog.records == []


def test_timeout_exactly_at_minimum_is_not_warned(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Catches <= instead of < in the warning condition: a spurious warning at
    # the legal boundary. The minimum is inclusive.
    with caplog.at_level(logging.WARNING):
        options = _parse(monkeypatch, "-t", "0.5")

    assert options.timeout_per_step == 0.5
    assert caplog.records == []


def test_zero_retries_is_legal_and_silent(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Options.min_retries is 0, so zero retries is valid. Catches treating it
    # as falsy and substituting the default, e.g. `options.args.retries or 1`.
    with caplog.at_level(logging.WARNING):
        options = _parse(monkeypatch, "-r", "0")

    assert options.retries == 0
    assert caplog.records == []


def test_negative_retries_is_clamped_to_zero_and_warned(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        options = _parse(monkeypatch, "-r", "-3")

    assert options.retries == 0
    assert "requested retries < minimum (0); bumping to 0" in caplog.text


def test_zero_workers_is_clamped_to_one_and_warned(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # A thread pool of zero hangs or throws inside emmykit.
    with caplog.at_level(logging.WARNING):
        options = _parse(monkeypatch, "-w", "0")

    assert options.workers == 1
    assert "requested workers < minimum (1); bumping to 1" in caplog.text


def test_no_exit_code_flag_inverts_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    # Catches a dropped `not`. The script would then exit 1 on success,
    # silently breaking every shell script that calls it.
    assert _parse(monkeypatch).exit_code is True
    assert _parse(monkeypatch, "--no-exit-code").exit_code is False


def test_each_boolean_flag_sets_only_its_own_attribute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # These three attributes are adjacent, same type, and set on consecutive
    # lines, so a swap is invisible by inspection. Comparing all three as a
    # tuple catches any pair being crossed.
    default = _parse(monkeypatch)
    assert (default.include_ipv6, default.strict, default.ignore_proxies) == (
        False,
        False,
        False,
    )

    ipv6 = _parse(monkeypatch, "--ipv6")
    assert (ipv6.include_ipv6, ipv6.strict, ipv6.ignore_proxies) == (True, False, False)

    strict = _parse(monkeypatch, "--strict")
    assert (strict.include_ipv6, strict.strict, strict.ignore_proxies) == (
        False,
        True,
        False,
    )

    proxies = _parse(monkeypatch, "--ignore-proxies")
    assert (proxies.include_ipv6, proxies.strict, proxies.ignore_proxies) == (
        False,
        False,
        True,
    )


def test_debug_flag_sets_the_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    # Catches the flag not reaching the log level -- which is exactly how
    # -debug was already inert once.
    assert _parse(monkeypatch).log_mode == logging.INFO
    assert _parse(monkeypatch, "-debug").log_mode == logging.DEBUG


def test_exit_code_reflects_connectivity(monkeypatch: pytest.MonkeyPatch) -> None:
    # Catches `0 if online else 1` inverted -- reporting failure on success.
    _, online_code = _run_main(monkeypatch, True)
    _, offline_code = _run_main(monkeypatch, False)

    assert (online_code, offline_code) == (0, 1)


def test_no_exit_code_suppresses_the_failing_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Catches the flag being ignored, so a monitor that only wants the message
    # still gets a failing exit status.
    _, code = _run_main(monkeypatch, False, "--no-exit-code")

    assert code is None


def test_main_passes_clamped_values_not_raw_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The seam between the file's two halves. options.args.timeout (raw) and
    # options.timeout_per_step (clamped) both exist on the same object, so
    # using the wrong one is a one-word slip that nothing else would catch.
    calls, _ = _run_main(monkeypatch, True, "-t", "0.1", "-w", "0", "-r", "-5")

    assert calls == [
        {
            "timeout_per_step": 0.5,
            "retries": 0,
            "workers": 1,
            "include_ipv6": False,
            "strict": False,
            "ignore_proxies": False,
        }
    ]


def test_offline_is_reported_at_warning_level(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    # Catches both results being logged at INFO, which makes an outage
    # invisible to anything filtering on severity.
    _run_main(monkeypatch, True)
    online_err = capfd.readouterr().err
    _run_main(monkeypatch, False)
    offline_err = capfd.readouterr().err

    assert " - INFO - Internet is available." in online_err
    assert " - WARNING - Internet is NOT available!" in offline_err
