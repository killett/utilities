# Making `utilities/` self-governing and clearing its lint debt

Date: 2026-08-14
Status: approved, not yet implemented

## Problem

`pixi run pre-commit run --all-files` has never been green for this repository
and cannot be made green today, for two independent reasons.

**The rules live somewhere else.** `utilities/` contains no `pyproject.toml`, no
`pixi.toml`, no `.pre-commit-config.yaml` and no installed git hook. Every ruff,
mypy, pytest and pre-commit setting comes from the surrounding `/workspace`
scaffold, which is regenerated and is not part of this repository. A fresh clone
of `utilities/` alone cannot be linted at all, and its runtime dependencies
(`emmykit`, `requests`, `beautifulsoup4`, `pandas`, `numpy`) are recorded only as
prose in `README.md`.

**33 ruff findings are outstanding**, in three files:

| File | Findings |
| --- | --- |
| `download_file.py` | 28 |
| `check_internet.py` | 3 |
| `test_parse_datetime.py` | 2 |

They are not 33 independent problems. They reduce to four root causes:

1. A pasted kitchen-sink `from typing import ...` line plus two stray imports —
   18 `F401` and both `UP035` findings, all in `download_file.py`.
2. Docstring summaries starting on line 2 instead of line 1 — 6 `D212`.
3. Two dead `assert options.args is not None` statements — 2 `S101`.
4. Import order, `class Options():`, one trailing space — 3 `I001`, 1 `UP039`,
   1 `W291`.

Separately, `test_parse_datetime.py` is not a test. It is 157 lines containing
72 top-level `print()` calls, zero test functions and zero live assertions (its
five `assert` lines are commented out). pytest imports it at collection, runs
every print, and collects nothing. It exercises `ek.parse_datetime` and
`ek.parse_timezone`, which **no script in this repository calls**, and it is the
sole reason `pandas` and `numpy` are needed at all.

## Goal

A repository that carries its own rules, is green under those rules, and does
not regenerate this debt when the next script is added.

## Decisions

| # | Decision | Rejected alternative and why |
| --- | --- | --- |
| 1 | `utilities/` becomes self-governing: its own `pyproject.toml`, `pixi.toml`, `pixi.lock` and `.pre-commit-config.yaml`, with the git hook installed | Staying scaffold-dependent: rules would exist only where the scaffold exists, and nothing would prevent regression in a fresh clone |
| 2 | One flat `[dependencies]` table, the union across all scripts | pixi features per script group: ~35 lines and a feature-to-script mapping that rots silently the moment a script gains an import. Not worth it for 10 scripts |
| 3 | `test_parse_datetime.py` is renamed to `demo_parse_datetime.py` and leaves pytest's collection path | Converting it: only 12 of 72 lines record an expected value, so the other 60 would be filled in by running the current emmykit and recording the output — implementation mirroring, which locks in today's behaviour including any bugs. Deleting it: destroys usable exploration notes |
| 4 | Format the whole repository once with `ruff format`, keeping the formatter in the hooks | Dropping ruff-format to preserve the hand-aligned annotation columns; or formatting on touch, which leaves the repo two-tier indefinitely and makes `--all-files` permanently unreachable |
| 5 | Add a checked-in `_template.py` | Relying on hooks alone: `F401` would stop another kitchen-sink import from landing, but the `Options` / `main()` / `__version__` shape would stay documented only as prose, so a structurally inconsistent script could still pass every hook |

## Design

### Configuration

`utilities/pyproject.toml` — tool configuration only, no packaging.

```toml
[project]
name = "utilities"
version = "0.1.0"  # PEP 621 requires it. Kept even without [build-system] so
                   # any uv-using tool that walks into this directory validates.
requires-python = ">=3.12,<3.14"

[tool.ruff.lint]
select = ["F", "E", "W", "B", "B9", "UP", "I", "ANN", "D", "S"]
ignore = [
    "E501",    # line length is ruff format's job
    "D100",    # module docstring — these are scripts, not library modules
    "ANN204",  # return type on __init__
]

[tool.ruff.lint.per-file-ignores]
"test_*.py" = ["ANN", "D", "S"]  # tests assert and do not need docstrings
# A pattern with no path separator matches the basename. The scaffold's version
# used "**/test_*.py" because the files sat one directory down; here they are at
# the root. Commit 1's finding-count gate confirms the pattern actually applies —
# if it silently missed, the count would balloon by roughly 150 rather than
# staying at 33.

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
addopts = "-v"
pythonpath = ["."]   # flat layout: tests import scripts as top-level modules

[tool.coverage.run]
source = ["."]
omit = ["test_*.py", "demo_*.py", "_template.py"]
```

Three deliberate departures from the scaffold's version:

- **No `[[tool.mypy.overrides]] module = ["tests.*"]`.** It never matched
  anything here — the tests are flat, and mypy rejects `test_*` as a pattern
  ("Patterns must be fully-qualified module names"). Flat test files stay
  annotated instead, which they already are. Carrying a dead override forward
  would be exactly the kind of debt this work removes.
- **No `mypy_path` and no `PYTHONPATH=src`.** There is no `src/` layout.
- **`D104` dropped from the ignore list.** There are no packages, so it can
  never fire.

No per-file-ignore is needed for `demo_*.py`: linting the renamed file in
isolation under this exact rule set produces only `I001` and `W291`, both fixed
in commit 5.

`utilities/pixi.toml`:

```toml
[workspace]
name = "utilities"
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "osx-64"]
exclude-newer = "7d"

[dependencies]
python = ">=3.12,<3.14"
# dev tooling
ruff = "*"
mypy = "*"
pytest = "*"
pytest-cov = "*"
pre-commit = "*"
# runtime, union across all scripts
requests = "*"          # download_torrents.py
beautifulsoup4 = "*"    # download_torrents.py
pandas = "*"            # demo_parse_datetime.py
pandas-stubs = "*"      # so mypy can see pandas
numpy = "*"             # demo_parse_datetime.py

[pypi-dependencies]
emmykit = { version = ">=0.3.4", extras = ["lint"] }  # lint extra is myaudit.py's

[tasks]
test = "python -m pytest"
test-cov = "python -m pytest --cov"
lint = "python -m ruff check ."
format = "python -m ruff format ."
typecheck = "python -m mypy ."
pre-commit = "python -m pre_commit"
pre-commit-all = "python -m pre_commit run --all-files"
pre-commit-install = "python -m pre_commit install --install-hooks"
```

Each runtime dependency carries a comment naming the script that needs it, since
a flat table otherwise loses that information. `emmykit` floats at `>=0.3.4`:
the adoption work is landed, so 0.4.0's removal of the script constants no
longer affects anything, and `pixi.lock` pins the exact build.

### Enforcement

`utilities/.pre-commit-config.yaml` mirrors the scaffold's shape, which is
already proven in this environment: all hooks `local`, everything routed through
`pixi run python -m <tool>`, no remote repositories, so no network at commit
time and every tool is the one pinned in `pixi.lock`.

```yaml
repos:
  - repo: local
    hooks:
      # `python -m <tool>` dodges a macOS shebang-resolution problem with
      # pixi-installed console scripts.
      - id: ruff
        name: ruff
        entry: pixi run python -m ruff check --fix
        language: system
        types: [python]
      - id: ruff-format
        name: ruff-format
        entry: pixi run python -m ruff format
        language: system
        types: [python]
      - id: mypy
        name: mypy
        entry: pixi run python -m mypy .
        language: system
        types: [python]
        pass_filenames: false
      - id: check-merge-conflict
        name: check-merge-conflict
        entry: '^(<<<<<<< |>>>>>>> |={7}$)'
        language: pygrep
      - id: check-added-large-files
        name: check-added-large-files (limit 500 KB)
        entry: 'bash -c ''max=500000; rc=0; for f in "$@"; do sz=$(wc -c < "$f"); if (( sz > max )); then echo "$f: $sz bytes exceeds limit of $max" >&2; rc=1; fi; done; exit $rc'' --'
        language: system
      - id: check-toml
        name: check-toml
        entry: 'pixi run python -c ''import sys,tomllib;[tomllib.load(open(f,"rb")) for f in sys.argv[1:]]'''
        language: system
        types: [toml]
```

Two properties make the commit ordering below work:

- `ruff` and `ruff-format` see **staged files only**, so each cleanup commit is
  judged on the file it touches, not on the ones still dirty.
- `mypy` is `pass_filenames: false` with `mypy .`, so it checks the **whole
  repository on every commit**. This is deliberate: a change in `printall.py`
  can break `test_printall.py`, and a staged-files-only run would miss it. It is
  affordable because mypy is already green across all current files.

`.gitignore` gains `.pixi/`. `pixi.lock` is committed, not ignored — it is what
makes the flat dependency list reproducible rather than aspirational.

### Code changes

**`download_file.py`.** Delete the 18 unreferenced imports on lines 8, 10 and 11
— which also removes both `UP035` findings, since they sit on the same paste
line. `class Options():` becomes `class Options:`. Four docstring summaries move
onto the opening line.

The two `assert options.args is not None` statements (lines 61 and 117) are
**deleted, not converted to raises**. `self.args` is declared
`argparse.Namespace`, never `Optional`, so the assert narrows nothing for mypy
and guards nothing at runtime; under `python -O` it would not exist at all. It
is dead code that happens to trip `S101`. Had either been a real invariant
check, it would become a `raise` instead.

**`check_internet.py`.** Import sort and two docstring summaries. Nothing
semantic.

**`test_parse_datetime.py` → `demo_parse_datetime.py`.** `git mv` so history
follows, then fix `I001` and `W291`. Lines 153–157 hold five commented-out
assertions with hand-derived expected values for Julian and ordinal dates.
Those are the only genuinely test-shaped content in the file, and the
expectations are hand-written rather than derived from running the code — so
they are the seed if real coverage of those parsers is ever wanted. This work
does not act on them.

**Repo-wide `ruff format`.** `ruff format` mangles long trailing comments into

```python
        self.my_name: str = Path(
            sys.argv[0]
        ).stem  # The invoked name of this script without the extension
```

which is worse than what it replaces. The established fix, already applied to
the six adopted scripts, is to move such comments onto their own line above,
after which the formatter leaves the statement intact. That is a judgement call,
not mechanical, so it happens inside the per-file commits (3 and 4). Commit 6 is
then a genuinely pure `ruff format .` over `detect_country.py` and
`demo_parse_datetime.py`.

**`_template.py`.** The leading underscore keeps pytest from collecting it,
keeps coverage from measuring it, and sorts it to the top of a listing. It is a
real linted file, so it cannot silently rot.

```python
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Most scripts here also:  import emmykit as ek

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
```

plus `parse_arguments()` carrying the `-v`/`--version` and `-debug`/`--debug`
pair, a `main()` that configures logging and calls `logging.shutdown()`, and the
`if __name__ == "__main__":` guard.

The emmykit line is a **comment, not an import**. A speculative
`import emmykit as ek` would be `F401` — the template would ship the exact
defect it exists to prevent.

### Documentation

`README.md`: the structure table gains `_template.py` and
`demo_parse_datetime.py`; the "Tests live alongside the scripts" line gains the
`demo_*` and `_template` naming rule; installation grows a `pixi install` path
alongside the existing `pip install` one for running a single script standalone.
It also gains the new `docs/` directory.

`CLAUDE.md` currently documents only the commit-message convention. It gains a
tooling section: run tools via `pixi run` **from this directory**; start new
scripts from `_template.py`; `test_*` means real assertions and `demo_*` means
exploratory prints; the `ruff` hook mutates staged files, so a failed commit
means re-add and retry.

That CLAUDE.md edit is the highest-leverage item here. The rest fixes debt that
exists; that one stops a future session from recreating it.

## Commit sequence

Foundation first, so every cleanup commit is performed under the rules that will
govern the repository permanently, rather than under the outer scaffold's. One
commit each, following the repository's `<script-name>: <type>: <description>`
convention.

| # | Commit | Gate |
| --- | --- | --- |
| 1 | `chore: add pyproject.toml and pixi.toml, ignore .pixi/` | `pixi install` succeeds and `pixi.lock` covers all three platforms; `pixi run lint` reports **exactly 37 findings** — see the correction note below |
| 1b | `tests: style: regroup sibling-script imports as first-party` | 37 → 33; `pytest` still reports 35 passed; only import blocks change |
| 2 | `chore: add pre-commit config and install the hook` | `pixi run pre-commit-install`, then commit — the whole-repo `mypy` hook must pass |
| 3 | `download_file.py: refactor: drop dead imports and asserts` | 33 → 5 findings; `python download_file.py --help` returns 0 |
| 4 | `check_internet.py: docs: fix docstring summary placement` | 5 → 2; `--help` returns 0 |
| 5 | `test_parse_datetime.py: refactor: demote to demo_parse_datetime.py` | 2 → 0; **pytest still reports 35 passed** |
| 6 | `chore: format the repo with ruff format` | `ruff format` idempotent on re-run; lint still clean; still 35 tests |
| 7 | `_template.py: feat: add a clean starting point for new scripts` | `python _template.py --help` returns 0 and a bare run works |
| 8 | `docs: update README and CLAUDE.md for the new layout` | no `test_parse_datetime` references outside git history |

The commit-5 gate is the falsifiable form of the claim that the file was never a
test. If the count moves off 35, that claim was wrong.

Commit 1's finding-count gate is the guard against the new configuration
silently diverging from the old one. A different number means reconciling
before anything is built on top.

**Correction, found while executing commit 1.** That gate originally read
"exactly 33". The real number is 37, and this document was wrong rather than
the implementation. Moving the config into `utilities/` changes ruff's isort
project root: under `/workspace/pyproject.toml`, `src` resolved to a directory
containing no `printall.py`, so `import printall` was classified third-party
and sorted next to `pytest`; under the in-tree config, `src` resolves here,
where the script does exist, so it is first-party and belongs in its own
block. Four test modules import a sibling script and are affected —
`test_printall.py`, `test_mydiff.py`, `test_multireplace.py` and
`test_treeview.py`. The new grouping is the more correct one; the original 33
was measured under a config that misclassified these imports. Commit 1b
applies the four `ruff --fix` auto-fixes, after which the count is 33 and
every later gate in the table holds as written. This is the one exception to
the out-of-scope note that no `test_*.py` would be touched.

Two edits sit outside this sequence and should not be looked for in it. This
spec is committed to `utilities/` before commit 1, which is what introduces the
`docs/` directory that commit 8's README update then documents. And the
`extend-exclude` / `exclude` additions in the risk table below modify
`/workspace`, a different repository, so they are a loose edit there rather than
a commit here.

## Acceptance criteria

```
pixi run lint           → All checks passed!               (was: 33 findings)
pixi run format --check → 17 files already formatted
pixi run typecheck      → Success: no issues in 17 source files
pixi run test           → 35 passed
pixi run pre-commit-all → every hook Passed                (currently unreachable)
```

Seventeen files: nine scripts, six test modules, one demo, one template.

`pixi run format --check` works because pixi forwards trailing arguments to the
task, making it `ruff format . --check`.

## Risks

| Risk | Response |
| --- | --- |
| `pandas-stubs` or `emmykit[lint]` fails to solve on `osx-arm64` / `osx-64` | Move to `[target.linux-64.dependencies]`. Caught at commit 1, before anything is built on it. The `pixi.lock` solve is the proof; no Mac required |
| New ruff config surfaces findings the outer one did not | The "exactly 33" gate at commit 1 catches it while reconciling is still cheap |
| `ruff format` produces a large diff on the 157-line demo | Accepted. Isolated in commit 6, and it is a demo |
| The `ruff --fix` hook mutates staged files mid-commit | Expected pre-commit behaviour. Documented in CLAUDE.md so a failed commit reads as "re-add and retry" rather than as breakage |
| Two sources of truth: `/workspace` still lints `utilities/` under its own rules | Add `extend-exclude = ["utilities"]` and `exclude = ["^utilities/"]` to the outer configs. Hygiene only, not durable — the scaffold is regenerated. The real guarantee is running tools from inside `utilities/`, which the new `[tasks]` make natural |

## Out of scope

Recorded as decisions, not oversights.

- **`check_internet.py`, `detect_country.py` and `download_file.py` remain
  untested.** Each is a thin wrapper over a single `emmykit` call, and this work
  is about lint debt, not test coverage. `download_file.py` undergoes import
  surgery here, so it is verified by import plus `--help` rather than by new
  tests.
- **Converting `demo_parse_datetime.py` into a real test suite.** See decision 3.
- **The outer scaffold's `pixi.toml`** keeps the `emmykit`, `pandas`,
  `pandas-stubs` and `beautifulsoup4` entries added earlier. Now redundant,
  harmless, and the scaffold is disposable.
