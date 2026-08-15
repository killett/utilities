# Rigorous tests for `check_internet.py`, `detect_country.py` and `download_file.py`

Date: 2026-08-15
Status: approved, not yet implemented

## Problem

Six of this repo's nine scripts have tests. These three do not. They were left
out of the previous cycle deliberately — that work was about lint debt, not
coverage — and the omission was recorded rather than fixed.

Probing `download_file.determine_destination_path()` while scoping this work
turned up two real defects, so this is not purely a test-writing exercise.
Actual output from the current code:

```
'https://example.com/dir/file.bin'       -> '/tmp/dl/file.bin'          correct
'https://example.com/file.bin?v=2#frag'  -> '/tmp/dl/file.bin'          correct
'https://example.com'                    -> '/tmp/dl/example.com'       intended fallback
''                                       -> '/tmp/dl/download-<ts>'     intended fallback
'https://example.com/a/b/../..'          -> '/tmp/dl/..'                escapes dest_dir
'https://example.com/my%20file.bin'      -> '/tmp/dl/my%20file.bin'     never decoded
```

`/tmp/dl/..` is the parent of the download directory: a URL decides where the
write lands. And percent-encoding is never decoded, though the sibling
`download_torrents.py` does `unquote()` in its `safe_filename_from_url()`, so
the repo is inconsistent with itself.

Also dead: `base_name.replace("/", "_")`. A netloc cannot contain `/`, and
neither can the timestamp string.

## Goal

Tests that can actually fail, for the parts of these three scripts that carry
logic — and fixes for the defects those tests expose.

## Decisions

| # | Decision | Rejected alternative and why |
| --- | --- | --- |
| 1 | Tests assert correct behaviour; where the code disagrees, the code changes | Asserting current behaviour would encode the defects as intended, which is the implementation-mirroring the test-design standard forbids. Marking the bad cases `xfail` documents them but leaves them live |
| 2 | An unusable filename candidate falls through to the existing host/timestamp fallback | Raising `ValueError` — louder, but adds an exception to a function whose docstring says `Raises: None` and needs new handling in `run_download` and `main`. Character sanitising via `download_torrents.py`'s regex does not work: dots and word characters survive it, so `..` passes through unchanged |
| 3 | No `--cov-fail-under`; coverage stays informational | A threshold over ten unrelated standalone scripts measures which happen to be testable, not whether the code is good. `detect_country.py` can reach 100% and prove almost nothing |
| 4 | Two capture mechanisms, `caplog` before `basicConfig` and `capfd` after | Using `caplog` throughout fails silently — see "The capture rule" below |
| 5 | `Options.default_dest_dir` gets wired up rather than deleted | Deleting it also means deleting three docstring lines that promise it. Wiring it makes those true and uses the `.resolve()`d path instead of a possibly-symlinked `cwd` |
| 6 | No shared filename helper extracted between `download_file.py` and `download_torrents.py` | These are deliberately standalone scripts with no package to import. Consistency is achieved by making them behave the same, not by coupling them |

## The capture rule

`logging.basicConfig(force=True)` removes every root handler, and pytest's
`caplog` works by installing one. Verified directly:

```
after main():   caplog records = 0
                capfd stderr   = '2026-08-15 12:10:49 - INFO - Detected country: NL\n'
```

Before `basicConfig` runs, `caplog` works normally — `check_internet.parse_arguments()`
emits its warnings at that point and they are captured (2 records observed).

So: **`caplog` for anything called before `main()` configures logging; `capfd`
for anything that drives `main()`.** Getting this backwards produces an empty
assertion that passes, so each test file carries a comment stating the rule.

## Production change: `determine_destination_path()`

**The ordering trap.** Adding `unquote()` alone would *introduce* a traversal
that does not exist today. `https://example.com/%2E%2E` currently yields the
literal filename `%2E%2E` — ugly but harmless. Decoded, it becomes `..`. The
decode and the guard must land together, and test 5 below exists to keep them
paired.

**Second finding.** The fallback uses `parsed.netloc`, which carries userinfo
and port: `https://user:pass@example.com:8080` writes a file named
`user:pass@example.com:8080` — credentials on disk, in a filename.
`parsed.hostname` yields `example.com`, cannot contain `/`, and so also retires
the dead `.replace("/", "_")`.

```python
    parsed = urlparse(url)
    # Take the name first, then decode: decoding first would let %2F inject a
    # separator and silently retarget the download.
    candidate = unquote(Path(parsed.path).name) if parsed.path else ""

    # "", "." and ".." are not usable filenames, and ".." would resolve outside
    # dest_dir. A decoded separator is equally unusable. All fall back.
    if candidate in {"", ".", ".."} or "/" in candidate or "\\" in candidate:
        import datetime as dt

        current_timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        # hostname, not netloc: netloc carries userinfo and port, so a URL with
        # credentials would write them into the filename.
        candidate = parsed.hostname or f"download-{current_timestamp}"

    return Path(dest_dir) / candidate
```

`run_download` additionally changes from `determine_destination_path(url, Path.cwd())`
to `determine_destination_path(url, options.default_dest_dir)`, per decision 5.

## Tests

Every test below names the behaviour, the concrete bug that would make it fail,
and where its expected value came from. Expected values are derived from the
URL, from RFC 3986, or from the `Options` defaults — never by running the code.

### `test_download_file.py`

`determine_destination_path`:

| # | Behaviour | Bug it catches | Expected value from |
| --- | --- | --- | --- |
| 1 | `/dir/file.bin` → `dest/file.bin` | using the host unconditionally, so every download lands under the host name | reading the URL |
| 2 | `file.bin?v=2#frag` → `dest/file.bin` | matching the raw URL instead of `urlparse().path`, giving an illegal filename | RFC 3986: query and fragment are not path |
| 3 | `my%20file.bin` → `dest/my file.bin` | today's behaviour — no decode, so the file is literally named `my%20file.bin` | RFC 3986: `%20` is a space |
| 4 | `/a/b/../..` → `dest/example.com` | today's behaviour — returns `dest/..`, the parent of the download directory | the documented host fallback |
| 5 | `/%2E%2E` → `dest/example.com` | adding `unquote` without the guard; keeps the two halves of the fix paired | same as 4 |
| 6 | `/a%2Fb.bin` → `dest/example.com` | decode-then-split, which silently downloads `b.bin` instead of what the URL named | neither `a/b.bin` nor `b.bin` is a filename the URL asked for |
| 7 | `https://user:pass@example.com:8080` → `dest/example.com` | using `netloc`, writing credentials into the filename | RFC 3986 authority grammar |
| 8 | `""` → `dest/download-<8 digits>_<6 digits>` | a broken fallback chain producing an empty filename | the `%Y%m%d_%H%M%S` format string, asserted by regex so no clock is frozen and no dependency is added |
| 9 | same URL, two `dest_dir` values → two different parents | hardcoding `Path.cwd()` and ignoring the argument | the argument itself |

Tests 3 through 7 fail against the code as it stands. That is the point: they
are the fix's proof, not a description of it.

`run_download`, with `ek.download_file` stubbed to record its call:

| # | Behaviour | Bug it catches |
| --- | --- | --- |
| 10 | `ek.download_file` receives the URL, and a destination whose parent is `options.default_dest_dir` | swapped or mis-keyed arguments (the call site uses `url=`, `dest=`, `timeout=`), and the decision-5 wiring silently reverting to `Path.cwd()` |
| 11 | an existing destination logs a warning naming the path | silently overwriting a file the user already had |

Test 11 uses `caplog`: `run_download` is called directly, so `basicConfig` has
not run.

### `test_check_internet.py`

No production changes; the logic is correct. The risk is that the clamping
arithmetic and the exit-code contract are both easy to break invisibly.

`parse_arguments`:

| # | Behaviour | Bug it catches | Expected value from |
| --- | --- | --- | --- |
| 1 | `-t 0.1` → `0.5`, warning names `0.5` | `min()` where `max()` belongs, or clamping to the wrong bound | `Options.min_timeout` |
| 2 | `-t 10` → `10.0`, no warning | clamping unconditionally to the default. Without this, `timeout = min_timeout` always would pass test 1 | the argument itself |
| 3 | `-t 0.5` → `0.5`, no warning | `<=` instead of `<` in the warning condition, warning at the legal boundary | the minimum is inclusive |
| 4 | `-r 0` → `0`, no warning | treating 0 as falsy and substituting the default, e.g. `options.args.retries or 1` | `Options.min_retries`, which is 0 |
| 5 | `-r -3` → `0`, with a warning | no lower bound on retries | same |
| 6 | `-w 0` → `1`, with a warning | a thread pool of zero, which hangs or throws inside `emmykit` | `Options.min_workers` |
| 7 | `--no-exit-code` → `exit_code is False`; absent → `True` | dropping the `not`, so the script exits 1 on success and breaks every shell script calling it | the flag name is a negation |
| 8 | `--ipv6` / `--strict` / `--ignore-proxies` each set their own attribute, all defaulting `False` | wiring a flag to a neighbouring attribute; they are adjacent, same type, and a swap is invisible by inspection | one flag per attribute |
| 9 | `-debug` → `log_mode == logging.DEBUG`; absent → `INFO` | the flag not reaching the log level, which is how `-debug` was already inert once | `Options.log_mode` default |

Tests 1 to 3 examine one boundary from three sides. Any one alone passes
against a broken implementation; together they pin it.

`main`, with `ek.is_internet_available` stubbed:

| # | Behaviour | Bug it catches |
| --- | --- | --- |
| 10 | online → `SystemExit(0)`; offline → `SystemExit(1)` | the `0 if online else 1` inverted, reporting failure on success |
| 11 | `--no-exit-code` with an offline result → returns normally, no `SystemExit` | the flag ignored, so a monitor that only wants the message still gets a failing status |
| 12 | `-t 0.1 -w 0` → `is_internet_available` receives `timeout_per_step=0.5, workers=1` | passing `options.args.timeout` (raw) instead of `options.timeout_per_step` (clamped). Both live on the same object; the slip is one word and nothing else would catch it |
| 13 | offline emits a `WARNING` line, online an `INFO` one | both logged at INFO, making an outage invisible to anything filtering on severity |

Test 12 is the seam between the file's two halves. Every other test passes
whether or not it is wired correctly.

### `test_detect_country.py`

| # | Behaviour | Bug it catches |
| --- | --- | --- |
| 1 | `ek.detect_country` called with `force_wtfismyip=False` | flipped to `True`, silently switching to a different provider with different availability and rate limits. The `False` was deliberate and nothing else records it |
| 2 | the returned country appears in the output | logging a stale variable or the wrong f-string field — the script's whole purpose, invisible |
| 3 | the line matches `YYYY-MM-DD HH:MM:SS - INFO - Detected country: <value>` | `force=True` removed from `basicConfig`; `emmykit`'s import-time handler then wins, the format reverts, and `-debug` goes inert across the repo |

Test 3 is why this 12-line file gets tests. That bug shipped in four scripts
and survived until commit `4a55674`. This is the cheapest place to pin it:
`main()` is three lines and always emits exactly one INFO line.

## Layout and mechanics

Three new files — `test_check_internet.py`, `test_detect_country.py`,
`test_download_file.py` — flat alongside the scripts, matching the existing
six. No `conftest.py`: each file stubs `emmykit` at the specific function it
needs, `test_mydiff.py` already keeps its fixture local, and a shared file
would couple three unrelated scripts for no gain.

No test touches the network. Flat test files carry real type annotations,
because mypy rejects `test_*` override patterns — established in the previous
cycle and recorded in `pyproject.toml`.

## Verification

- `pixi run lint`, `pixi run format --check`, `pixi run typecheck` and
  `pixi run pre-commit-all` all stay green.
- The suite grows from 35 tests to roughly 62.
- Because `CLAUDE.md` mandates red/green: tests 3 to 7 of `test_download_file.py`
  are run against the **unfixed** code first and their failure output captured,
  then the fix lands and they go green. Genuine TDD here rather than
  retrofitted, since those tests describe behaviour the code does not yet have.
- `pixi run test-cov` is recorded before and after as an informational number,
  with no threshold enforced.

## Out of scope

- A coverage threshold. See decision 3.
- Extracting a shared URL-to-filename helper. See decision 6.
- `download_torrents.py`'s own `safe_filename_from_url()`, which already
  unquotes and already has tests from the previous cycle.
- The remaining scripts. `printall.py`, `mydiff.py`, `myaudit.py`,
  `multireplace.py` and `treeview.py` were tested in the previous cycle.
