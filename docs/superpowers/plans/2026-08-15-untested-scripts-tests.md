# Tests for the Three Untested Scripts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 27 tests covering `check_internet.py`, `detect_country.py` and `download_file.py`, and fix the three `determine_destination_path()` defects those tests expose.

**Architecture:** Three new flat test files, one per script, matching the existing six. `emmykit` is stubbed with `monkeypatch.setattr` at the specific function each test needs, so nothing touches the network. Task 3 is genuine red/green: five of its tests are run against the unfixed code and their failure captured before the fix lands.

**Tech Stack:** pytest, pytest's `monkeypatch` / `caplog` / `capfd` / `tmp_path` fixtures. No new dependencies.

**Global Constraints:**
- Every command runs from `/workspace/utilities`. `pixi run` resolves the manifest there.
- **The capture rule.** `logging.basicConfig(force=True)` removes every root handler, and `caplog` works by installing one. Verified: `caplog` captures **0** records after `main()` runs, while `capfd` sees the real stderr line. Use `caplog` only for code called *before* `main()` configures logging (`parse_arguments`, `run_download` called directly); use `capfd` for anything that drives `main()`. Getting this backwards yields an assertion that passes against an empty string.
- Flat test files carry real type annotations — mypy is strict and rejects `test_*` override patterns.
- Expected values come from the URL, from RFC 3986, or from the `Options` defaults. Never run the code to find out what to assert.
- Commit messages follow `<script-name>: <type>: <description>`; exact messages are given per task.
- Do not modify `check_internet.py` or `detect_country.py`. Their logic is correct; only `download_file.py` changes.
- No `conftest.py`. Each test file is self-contained.
- No coverage threshold is added.

**User decisions (already made):**
- "Tests assert correct behaviour, fix the code" — where the code disagrees with a test, the code changes. Do not assert current behaviour and do not use `xfail`.
- "Fall through to the existing fallback" — an unusable filename candidate uses the host, then the timestamp. Do not raise, and do not try to sanitise characters.
- "No threshold, report only" — no `--cov-fail-under`.
- Wire up `Options.default_dest_dir` rather than deleting it.

**Spec:** `docs/superpowers/specs/2026-08-15-untested-scripts-test-design.md`

---

## File Structure

| Path | Responsibility | Task |
| --- | --- | --- |
| `test_detect_country.py` | 3 tests. Establishes the `capfd` pattern the later files reuse. | 1 (create) |
| `test_check_internet.py` | 13 tests: 9 on clamping via `caplog`, 4 on the exit-code contract via `capfd`. | 2 (create) |
| `test_download_file.py` | 9 tests on `determine_destination_path`, then 2 on `run_download`. | 3 (create), 4 (extend) |
| `download_file.py` | The `determine_destination_path` fix, and the `default_dest_dir` wiring. | 3, 4 (modify) |

Task 1 comes first because it is the smallest file that exercises the `capfd`
rule, so the pattern is established before the larger files depend on it.

---

### Task 1: Tests for `detect_country.py`

**Goal:** Pin the two contracts of this 12-line script, and regression-test the log format that `basicConfig(force=True)` protects.

**Files:**
- Create: `/workspace/utilities/test_detect_country.py`

**Acceptance Criteria:**
- [ ] `pixi run test` reports `38 passed` (35 existing + 3)
- [ ] `pixi run python -m ruff check test_detect_country.py` → `All checks passed!`
- [ ] `pixi run typecheck` → `Success: no issues found in 18 source files`
- [ ] No test touches the network — `ek.detect_country` is stubbed in every one

**Verify:** `cd /workspace/utilities && pixi run test 2>&1 | tail -1` → `38 passed`

**Steps:**

- [ ] **Step 1: Create the test file**

```python
"""Tests for detect_country.py."""

from __future__ import annotations

import re

import detect_country
import pytest

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

    monkeypatch.setattr(detect_country.ek, "detect_country", _record)

    detect_country.main()

    assert calls == [{"force_wtfismyip": False}]


def test_detected_country_reaches_the_output(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    # Catches logging a stale variable or the wrong f-string field -- the
    # script's entire purpose, silently absent.
    monkeypatch.setattr(detect_country.ek, "detect_country", lambda **kw: "Aotearoa")

    detect_country.main()

    assert "Detected country: Aotearoa" in capfd.readouterr().err


def test_log_line_keeps_its_configured_format(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    # Regression test for the force=True in basicConfig. emmykit installs a
    # root handler at import time, so without force=True basicConfig is a
    # documented no-op: the timestamp and level prefix vanish and -debug goes
    # inert across the repo. That bug shipped in four scripts once already.
    monkeypatch.setattr(detect_country.ek, "detect_country", lambda **kw: "NL")

    detect_country.main()

    err = capfd.readouterr().err.strip()
    assert LOG_LINE.match(err), f"log line lost its configured format: {err!r}"
```

- [ ] **Step 2: Run the tests**

```bash
cd /workspace/utilities && pixi run python -m pytest test_detect_country.py -v
```

Expected: 3 passed. These describe behaviour the code already has, so they are green immediately — unlike Task 3's, which are red first.

- [ ] **Step 3: Prove the third test can actually fail**

A test that cannot fail is worthless, and this one guards a subtle property. Temporarily delete the `force=True,` line from `detect_country.py`, re-run, and confirm `test_log_line_keeps_its_configured_format` FAILS with a message showing a bare `Detected country: NL` and no timestamp. Then restore the line:

```bash
cd /workspace/utilities
git diff --stat detect_country.py    # must be empty before moving on
```

- [ ] **Step 4: Lint, type-check and run the whole suite**

```bash
cd /workspace/utilities
pixi run python -m ruff check test_detect_country.py
pixi run python -m ruff format test_detect_country.py
pixi run typecheck 2>&1 | tail -1     # 18 source files
pixi run test 2>&1 | tail -1          # 38 passed
```

- [ ] **Step 5: Commit**

```bash
cd /workspace/utilities
git add test_detect_country.py
git commit -m "detect_country.py: test: cover the provider flag and log format

Three tests for a twelve-line script. Two pin its only contracts: that
ek.detect_country is called with force_wtfismyip=False, which selects
one provider over another and was recorded nowhere else, and that the
detected value reaches the output.

The third is a regression test for the force=True in basicConfig.
emmykit installs a root handler at import time, so without it
basicConfig is a no-op and the timestamp/level prefix disappears. That
bug shipped in four scripts and survived until 4a55674; main() here is
three lines and always emits exactly one INFO line, which makes this
the cheapest place to pin it."
```

---

### Task 2: Tests for `check_internet.py`

**Goal:** Pin the clamping arithmetic at every boundary and the exit-code contract that shell scripts depend on.

**Files:**
- Create: `/workspace/utilities/test_check_internet.py`

**Acceptance Criteria:**
- [ ] `pixi run test` reports `51 passed` (38 + 13)
- [ ] `pixi run python -m ruff check test_check_internet.py` → `All checks passed!`
- [ ] `pixi run typecheck` → `Success: no issues found in 19 source files`
- [ ] `check_internet.py` is unchanged — `git diff --stat check_internet.py` is empty
- [ ] `ek.is_internet_available` is stubbed in every test that reaches `main()`

**Verify:** `cd /workspace/utilities && pixi run test 2>&1 | tail -1` → `51 passed`

**Steps:**

- [ ] **Step 1: Create the file with its two helpers**

```python
"""Tests for check_internet.py."""

from __future__ import annotations

import logging
import sys
from typing import Any

import check_internet
import pytest

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

    monkeypatch.setattr(check_internet.ek, "is_internet_available", _stub)
    monkeypatch.setattr(sys, "argv", ["check_internet.py", *argv])
    try:
        check_internet.main()
    except SystemExit as exc:
        return calls, exc.code
    return calls, None
```

- [ ] **Step 2: Add the nine `parse_arguments` tests**

```python
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
```

- [ ] **Step 3: Add the four `main` tests**

```python
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
```

- [ ] **Step 4: Run, lint, type-check**

```bash
cd /workspace/utilities
pixi run python -m pytest test_check_internet.py -v 2>&1 | tail -3   # 13 passed
pixi run python -m ruff check test_check_internet.py
pixi run python -m ruff format test_check_internet.py
pixi run typecheck 2>&1 | tail -1     # 19 source files
pixi run test 2>&1 | tail -1          # 51 passed
git diff --stat check_internet.py     # must be empty
```

- [ ] **Step 5: Commit**

```bash
cd /workspace/utilities
git add test_check_internet.py
git commit -m "check_internet.py: test: cover clamping and the exit-code contract

Nine tests on parse_arguments() and four on main(). No production
change; the logic is correct, but both halves are easy to break
silently.

The clamping boundary is examined from three sides -- below, above and
exactly at the minimum -- because any one of those alone passes against
an implementation that always returns the minimum.

The most valuable of the four main() tests asserts that the *clamped*
values reach ek.is_internet_available. options.args.timeout and
options.timeout_per_step both live on the same object, so passing the
raw one is a single-word slip that no other test would catch."
```

---

### Task 3: Fix `determine_destination_path`, with red/green evidence

**Goal:** Fix the three defects in `determine_destination_path()` and prove the fix with tests that fail first.

**Files:**
- Create: `/workspace/utilities/test_download_file.py`
- Modify: `/workspace/utilities/download_file.py`

**Acceptance Criteria:**
- [ ] Before the fix, exactly 5 of the 9 new tests FAIL (tests 3–7 of the spec table)
- [ ] The captured failure output is pasted into the commit body
- [ ] After the fix, all 9 pass and `pixi run test` reports `60 passed` (51 + 9)
- [ ] `pixi run python -m ruff check test_download_file.py download_file.py` → `All checks passed!`
- [ ] `pixi run typecheck` → `Success: no issues found in 20 source files`
- [ ] `pixi run python download_file.py --help` exits 0

**Verify:** `cd /workspace/utilities && pixi run test 2>&1 | tail -1` → `60 passed`

**Steps:**

- [ ] **Step 1: Write the tests first, against the unfixed code**

```python
"""Tests for download_file.py."""

from __future__ import annotations

import re
from pathlib import Path

import download_file

DEST = Path("/tmp/dl")


def test_filename_comes_from_the_url_path() -> None:
    # Catches using the host unconditionally, so every download would land
    # under the host name instead of the file's own.
    assert (
        download_file.determine_destination_path(
            "https://example.com/dir/file.bin", DEST
        )
        == DEST / "file.bin"
    )


def test_query_and_fragment_are_not_part_of_the_filename() -> None:
    # RFC 3986: query and fragment are not part of the path. Catches matching
    # on the raw URL, which yields an illegal filename.
    assert (
        download_file.determine_destination_path(
            "https://example.com/file.bin?v=2#frag", DEST
        )
        == DEST / "file.bin"
    )


def test_percent_encoding_is_decoded() -> None:
    # RFC 3986: %20 is a space. download_torrents.safe_filename_from_url()
    # already unquotes; this file did not, so the file landed on disk named
    # "my%20file.bin".
    assert (
        download_file.determine_destination_path(
            "https://example.com/my%20file.bin", DEST
        )
        == DEST / "my file.bin"
    )


def test_dot_dot_path_cannot_escape_the_destination_directory() -> None:
    # Previously returned DEST/"..", the PARENT of the download directory --
    # the URL decided where the write landed.
    assert (
        download_file.determine_destination_path(
            "https://example.com/a/b/../..", DEST
        )
        == DEST / "example.com"
    )


def test_encoded_dot_dot_cannot_escape_either() -> None:
    # This test keeps the two halves of the fix paired. Adding unquote() on
    # its own turns %2E%2E into a working "..", introducing a traversal that
    # does not exist today.
    assert (
        download_file.determine_destination_path("https://example.com/%2E%2E", DEST)
        == DEST / "example.com"
    )


def test_encoded_separator_does_not_retarget_the_download() -> None:
    # Decoding before splitting would silently yield "b.bin" -- a different
    # file from the one the URL named.
    assert (
        download_file.determine_destination_path(
            "https://example.com/a%2Fb.bin", DEST
        )
        == DEST / "example.com"
    )


def test_credentials_and_port_are_not_written_into_the_filename() -> None:
    # netloc is "user:pass@example.com:8080" -- using it writes credentials to
    # disk in a filename. hostname is "example.com" per RFC 3986's authority
    # grammar.
    assert (
        download_file.determine_destination_path(
            "https://user:pass@example.com:8080", DEST
        )
        == DEST / "example.com"
    )


def test_url_with_neither_path_nor_host_falls_back_to_a_timestamp() -> None:
    # Catches a broken fallback chain producing an empty filename. Asserted by
    # regex against the %Y%m%d_%H%M%S format string, so no clock is frozen and
    # no dependency is added.
    result = download_file.determine_destination_path("", DEST)

    assert result.parent == DEST
    assert re.fullmatch(r"download-\d{8}_\d{6}", result.name), result.name


def test_destination_directory_argument_is_respected(tmp_path: Path) -> None:
    # Catches hardcoding Path.cwd() and ignoring the argument.
    a = download_file.determine_destination_path(
        "https://example.com/f.bin", tmp_path / "a"
    )
    b = download_file.determine_destination_path(
        "https://example.com/f.bin", tmp_path / "b"
    )

    assert (a.parent.name, b.parent.name) == ("a", "b")
    assert a.name == b.name == "f.bin"
```

- [ ] **Step 2: Run them RED and capture the output**

```bash
cd /workspace/utilities
pixi run python -m pytest test_download_file.py -v 2>&1 | tee /tmp/red.txt | tail -20
```

Expected: `4 passed, 5 failed`. The five failures are
`test_percent_encoding_is_decoded`,
`test_dot_dot_path_cannot_escape_the_destination_directory`,
`test_encoded_dot_dot_cannot_escape_either`,
`test_encoded_separator_does_not_retarget_the_download` and
`test_credentials_and_port_are_not_written_into_the_filename`.

**If a different number fails, stop.** Fewer means a test is not actually
exercising the defect; more means the four "already correct" cases are not
correct after all, and the fix's shape needs rethinking before proceeding.

Keep `/tmp/red.txt` — one line per failure goes in the commit body at Step 5.

- [ ] **Step 3: Apply the fix**

Add `unquote` to the existing import:

```python
# before
from urllib.parse import urlparse

# after
from urllib.parse import unquote, urlparse
```

Then replace the body of `determine_destination_path` — everything from
`dest_dir_path: Path = Path(dest_dir)` to `return dest_path` — with:

```python
    parsed = urlparse(url)
    # Take the name first, then decode: decoding first would let %2F inject a
    # separator and silently retarget the download.
    candidate = unquote(Path(parsed.path).name) if parsed.path else ""

    # "", "." and ".." are not usable filenames, and ".." would resolve
    # outside dest_dir. A decoded separator is equally unusable. All fall back
    # to the host, then to a generic timestamped name.
    if candidate in {"", ".", ".."} or "/" in candidate or "\\" in candidate:
        import datetime as dt

        current_timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        # hostname, not netloc: netloc carries userinfo and port, so a URL
        # with credentials would write them into the filename.
        candidate = parsed.hostname or f"download-{current_timestamp}"

    return Path(dest_dir) / candidate
```

The docstring above it is unchanged and stays accurate, including `Raises: None`.

- [ ] **Step 4: Run them GREEN**

```bash
cd /workspace/utilities
pixi run python -m pytest test_download_file.py -v 2>&1 | tail -3   # 9 passed
pixi run python -m ruff check test_download_file.py download_file.py
pixi run python -m ruff format test_download_file.py download_file.py
pixi run typecheck 2>&1 | tail -1     # 20 source files
pixi run test 2>&1 | tail -1          # 60 passed
pixi run python download_file.py --help >/dev/null; echo "rc=$?"
```

- [ ] **Step 5: Commit, quoting the red run**

Replace the five `AssertionError` lines below with the actual first lines from
`/tmp/red.txt`.

```bash
cd /workspace/utilities
git add test_download_file.py download_file.py
git commit -m "download_file.py: fix: stop a URL choosing where the write lands

determine_destination_path() had three defects. Tests were written
first and five of the nine failed against the old code:

  test_percent_encoding_is_decoded
  test_dot_dot_path_cannot_escape_the_destination_directory
  test_encoded_dot_dot_cannot_escape_either
  test_encoded_separator_does_not_retarget_the_download
  test_credentials_and_port_are_not_written_into_the_filename

1. A path of /a/b/../.. returned dest_dir/.., the parent of the
   download directory, so the URL decided where the file was written.
2. Percent-encoding was never decoded, so a %20 in the URL became a
   literal '%20' in the filename -- inconsistent with the sibling
   download_torrents.safe_filename_from_url(), which unquotes.
3. The fallback used parsed.netloc, which carries userinfo and port, so
   https://user:pass@host writes the credentials into the filename.
   parsed.hostname is the authority's host alone, and cannot contain a
   slash -- which also retires the dead .replace('/', '_').

The decode and the traversal guard land together deliberately: adding
unquote() alone would turn %2E%2E into a working '..' and introduce a
traversal that did not previously exist. One test exists solely to keep
them paired."
```

---

### Task 4: Tests for `run_download`, and wire up `default_dest_dir`

**Goal:** Pin the delegation to `ek.download_file` and the overwrite warning, and make `Options.default_dest_dir` live so its three docstring references stop lying.

**Files:**
- Modify: `/workspace/utilities/test_download_file.py`
- Modify: `/workspace/utilities/download_file.py`

**Acceptance Criteria:**
- [ ] `pixi run test` reports `62 passed` (60 + 2)
- [ ] `run_download` reads `options.default_dest_dir`; `git grep -c 'Path.cwd()' download_file.py` returns 1 (the remaining debug log line only)
- [ ] `pixi run python -m ruff check .` → `All checks passed!`
- [ ] `pixi run pre-commit-all` → all 6 hooks `Passed`

**Verify:** `cd /workspace/utilities && pixi run test 2>&1 | tail -1` → `62 passed`

**Steps:**

- [ ] **Step 1: Wire up `default_dest_dir`**

In `run_download`, change the one call:

```python
# before
    dest_path: Path = determine_destination_path(url, Path.cwd())

# after
    dest_path: Path = determine_destination_path(url, options.default_dest_dir)
```

`Options.default_dest_dir` is `Path.cwd().expanduser().resolve()`, so this is
the same directory with symlinks resolved — and it makes the three docstrings
that already describe it ("Default directory where files will be saved") true.
Leave the `logging.debug("Current working directory: ...")` line alone; it
reports the cwd, which is still a useful thing to log.

- [ ] **Step 2: Add the two tests**

Add `import argparse` and `import logging` to the test file's imports, plus
`import pytest`, keeping them sorted — the final block is:

```python
import argparse
import logging
import re
from pathlib import Path

import download_file
import pytest
```

Then append:

```python
def _options_for(url: str, dest_dir: Path) -> download_file.Options:
    """Build an Options as parse_arguments() would leave it."""
    options = download_file.Options()
    options.default_dest_dir = dest_dir
    options.args = argparse.Namespace(url=url, debug=False)
    return options


def test_download_is_delegated_with_the_derived_destination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Catches swapped or mis-keyed arguments, and catches run_download
    # reverting to Path.cwd() instead of the configured destination.
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        download_file.ek, "download_file", lambda **kw: calls.append(kw)
    )

    download_file.run_download(_options_for("https://example.com/f.bin", tmp_path))

    assert calls == [
        {
            "url": "https://example.com/f.bin",
            "dest": tmp_path / "f.bin",
            "timeout": 10000,
        }
    ]


def test_existing_destination_is_warned_about(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # Catches silently overwriting a file the user already had. caplog works
    # here because run_download is called directly, so basicConfig has not run.
    (tmp_path / "f.bin").write_text("previous download", encoding="utf-8")
    monkeypatch.setattr(download_file.ek, "download_file", lambda **kw: None)

    with caplog.at_level(logging.WARNING):
        download_file.run_download(_options_for("https://example.com/f.bin", tmp_path))

    assert "already exists and will be overwritten" in caplog.text
    assert str(tmp_path / "f.bin") in caplog.text
```

- [ ] **Step 3: Verify**

```bash
cd /workspace/utilities
pixi run python -m pytest test_download_file.py -v 2>&1 | tail -3   # 11 passed
pixi run python -m ruff check test_download_file.py download_file.py
pixi run python -m ruff format test_download_file.py download_file.py
pixi run lint 2>&1 | tail -1          # All checks passed!
pixi run typecheck 2>&1 | tail -1     # 20 source files
pixi run test 2>&1 | tail -1          # 62 passed
pixi run pre-commit-all 2>&1 | rg -c Passed   # 6
pixi run test-cov 2>&1 | rg TOTAL     # informational, no threshold
```

- [ ] **Step 4: Commit**

```bash
cd /workspace/utilities
git add test_download_file.py download_file.py
git commit -m "download_file.py: test: cover run_download and wire default_dest_dir

Two tests: that ek.download_file receives the URL and the derived
destination with the expected keywords, and that an existing
destination is warned about rather than silently overwritten.

run_download now passes options.default_dest_dir rather than
Path.cwd(). The attribute was dead while three docstrings described it
as the directory files are saved to; it is the same directory with
symlinks resolved, and the first test pins the wiring so it cannot
quietly revert."
```

---

## Self-review

Checked against the spec:

- All 27 tests in the spec's three tables appear in a task — 3 in Task 1, 13 in Task 2, 9 in Task 3, 2 in Task 4.
- The production change in the spec's "Production change" section is Task 3 Step 3; the `run_download` half of it is Task 4 Step 1.
- Decision 5 (`default_dest_dir`) is Task 4.
- Decisions 3 and 6 require no work; they are constraints, recorded in the header.
- The capture rule appears as a comment in both test files that need it.
- Names used consistently: `determine_destination_path`, `run_download`, `Options.default_dest_dir`, `_parse`, `_run_main`, `_options_for`.
- Test counts chain: 35 → 38 → 51 → 60 → 62.
- mypy source-file counts chain: 17 → 18 → 19 → 20.
