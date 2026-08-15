# Utilities Self-Governing Lint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `utilities/` its own tooling configuration and clear all 33 outstanding ruff findings, so `pre-commit run --all-files` is green for the first time.

**Architecture:** Foundation first. `pyproject.toml`, `pixi.toml` and `.pre-commit-config.yaml` land before any Python is touched, so every cleanup commit is performed under the rules that will govern the repository permanently rather than under the surrounding `/workspace` scaffold's. The `ruff` and `ruff-format` hooks see staged files only, so each cleanup commit is judged on the file it touches; the `mypy` hook is whole-repo on every commit.

**Tech Stack:** pixi (conda-forge only), ruff, mypy (strict), pytest, pytest-cov, pre-commit. Runtime: emmykit 0.3.4+ with the `lint` extra, requests, beautifulsoup4, pandas, pandas-stubs, numpy.

**Global Constraints:**
- Every command runs from `/workspace/utilities`, not `/workspace`. After Task 1 the local `pixi.toml` is what `pixi run` resolves.
- Commit messages follow this repo's convention: `<script-name>: <type>: <description>`, with a bare `<type>: <description>` only for repo-wide changes. Exact messages are given in each task.
- conda-forge is the only conda channel. PyPI only for packages with no conda-forge build (`emmykit`).
- Never commit code that fails a hook. If the `ruff --fix` hook rewrites a staged file, re-add and retry — that is expected, not breakage.
- Do not modify the five adopted scripts (`printall.py`, `mydiff.py`, `myaudit.py`, `multireplace.py`, `treeview.py`), `download_torrents.py`, or any `test_*.py`. They are already clean; touching them is out of scope.
- The finding count is the running gate: 37 → 33 → 5 → 2 → 0. If a task's count does not match, stop and reconcile before proceeding. (See "Correction discovered during Task 1" below for why the first number is 37 and not 33.)
- Do not modify any `test_*.py` **except** the four import regroupings in Task 1b, which the new config's isort root makes mandatory.

**User decisions (already made):**
- "Self-governing" — `utilities/` carries its own `pyproject.toml`, `.pre-commit-config.yaml` and dependency declarations. Do not leave config in `/workspace`.
- "Flat env" — one `[dependencies]` table with the union of all scripts' needs. pixi features per script group were considered and rejected.
- "Demote to a demo script" — `test_parse_datetime.py` becomes `demo_parse_datetime.py`. Do not convert it to assertions and do not delete it.
- "Format everything once" — a one-off repo-wide `ruff format`, keeping the formatter in the hooks. The hand-aligned annotation columns are deliberately abandoned.
- "Checked-in script template" — add `_template.py`. Hooks alone were considered and rejected.

**Spec:** `docs/superpowers/specs/2026-08-14-utilities-self-governing-lint-design.md`

---

## Corrections to the spec, discovered by running the formatter

The spec predicted that `ruff format` would mangle long trailing comments in `check_internet.py` and `download_file.py`, and assigned a comment-repositioning step to Tasks 3 and 4. Running `ruff format --diff` against the real files shows otherwise:

- `check_internet.py` and `download_file.py` produce **zero** `= (` wraps. Their `Options` blocks collapse cleanly. **No comment repositioning is needed in Tasks 3 or 4.**
- The problem lands in `test_parse_datetime.py` instead, on **exactly 4 lines** (111, 117, 120, 129), where a long trailing comment forces a one-line `print(...)` into three lines. That repositioning moves to Task 5.

Task 6 therefore formats only `detect_country.py`: Tasks 3, 4 and 5 each stage a file, and the `ruff-format` hook formats staged files, so by Task 6 `detect_country.py` is the only unformatted file left.

## Correction discovered during Task 1

The plan originally gated Task 1 on `pixi run lint` reporting exactly 33 findings. The real number is **37**, and the plan was wrong rather than the implementation.

Moving the config into `utilities/` changes ruff's isort project root. With the config at `/workspace/pyproject.toml`, `src` resolved to `/workspace`, which contains no `printall.py`, so `import printall` was classified third-party and sorted alongside `pytest`. With the config at `utilities/pyproject.toml`, `src` resolves to `utilities/`, where `printall.py` does exist, so it is correctly first-party and belongs in its own block:

```diff
 import emmykit as ek
-import printall
 import pytest

+import printall
```

Four files import a sibling script and are affected: `test_printall.py`, `test_mydiff.py`, `test_multireplace.py`, `test_treeview.py`. The per-rule breakdown is otherwise identical to the original measurement, and the new grouping is the more correct one — the original 33 was measured under a config that was misclassifying these imports.

Per the user's ruling, Task 1 commits configuration only and gates on 37; the four auto-fixes land in a separate Task 1b, after which the count is 33 and every downstream gate holds as originally planned.

---

## File Structure

| Path | Responsibility | Task |
| --- | --- | --- |
| `pyproject.toml` | ruff / mypy / pytest / coverage configuration. No packaging. | 1 (create) |
| `pixi.toml` | Environment: channels, platforms, flat dependency table, `[tasks]`. | 1 (create) |
| `pixi.lock` | Exact resolved builds for all three platforms. Committed. | 1 (generated) |
| `.gitignore` | Add `.pixi/`. | 1 (modify) |
| `test_printall.py`, `test_mydiff.py`, `test_multireplace.py`, `test_treeview.py` | Import-block regrouping only, forced by the new isort root. | 1b (modify) |
| `.pre-commit-config.yaml` | Six local hooks, all via `pixi run python -m <tool>`. | 2 (create) |
| `download_file.py` | 28 of the 33 findings. | 3 (modify) |
| `check_internet.py` | 3 findings. | 4 (modify) |
| `demo_parse_datetime.py` | Renamed from `test_parse_datetime.py`; 2 findings plus 4 comment moves. | 5 (rename + modify) |
| `detect_country.py` | Formatting only. | 6 (modify) |
| `_template.py` | Clean starting point for new scripts. Linted, so it cannot rot. | 7 (create) |
| `README.md` | Structure table, naming rules, install paths. | 8 (modify) |
| `CLAUDE.md` | Tooling conventions. | 8 (modify) |

---

### Task 1: Configuration and environment

**Goal:** `utilities/` carries its own ruff/mypy/pytest config and a reproducible pixi environment, reporting the same 33 findings the outer scaffold did.

**Files:**
- Create: `/workspace/utilities/pyproject.toml`
- Create: `/workspace/utilities/pixi.toml`
- Create: `/workspace/utilities/pixi.lock` (generated by `pixi install`)
- Modify: `/workspace/utilities/.gitignore`

**Acceptance Criteria:**
- [ ] `pixi install` succeeds and writes `pixi.lock`
- [ ] `pixi.lock` contains solved packages for `linux-64`, `osx-arm64` and `osx-64`
- [ ] `pixi run lint` reports exactly `Found 37 errors.`
- [ ] `pixi run python -m ruff check test_printall.py --statistics` reports `1 I001` and nothing else — proving the `test_*.py` per-file-ignore pattern matches (no `ANN`, `D` or `S` findings in a file full of bare `assert`s), while the single `I001` is the expected first-party reclassification that Task 1b fixes
- [ ] `pixi run typecheck` reports `Success: no issues found in 16 source files`
- [ ] `pixi run test` reports `35 passed`
- [ ] `.pixi/` is gitignored and `pixi.lock` is committed

**Verify:** `cd /workspace/utilities && pixi run lint 2>&1 | tail -2` → `Found 37 errors.`

**Steps:**

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "utilities"
version = "0.1.0"  # PEP 621 requires it. Kept even without [build-system] so any
                   # uv-using tool that walks into this directory still validates.
requires-python = ">=3.12,<3.14"

[tool.ruff.lint]
select = [
    "F",    # Pyflakes — unused imports, undefined names
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "B",    # flake8-bugbear
    "B9",   # bugbear opinionated rules
    "UP",   # pyupgrade
    "I",    # isort
    "ANN",  # flake8-annotations
    "D",    # pydocstyle
    "S",    # bandit
]
ignore = [
    "E501",    # line length is ruff format's job
    "D100",    # module docstring — these are scripts, not library modules
    "ANN204",  # return type annotation on __init__
]

# A pattern with no path separator matches the basename. The scaffold's version
# used "**/test_*.py" because the files sat one directory down; here they are at
# the repo root. Task 1 verifies the pattern actually matches.
[tool.ruff.lint.per-file-ignores]
"test_*.py" = ["ANN", "D", "S"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
strict = true
warn_return_any = true
warn_unused_configs = true
# Deliberately no [[tool.mypy.overrides]] for tests: mypy rejects patterns like
# "test_*" ("Patterns must be fully-qualified module names"), and this repo's
# tests are flat rather than under tests/. They carry real annotations instead.
# Deliberately no mypy_path: there is no src/ layout.

[tool.pytest.ini_options]
addopts = "-v"
pythonpath = ["."]  # flat layout: tests import the scripts as top-level modules

[tool.coverage.run]
source = ["."]
omit = ["test_*.py", "demo_*.py", "_template.py"]
```

- [ ] **Step 2: Create `pixi.toml`**

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
requests = "*"        # download_torrents.py
beautifulsoup4 = "*"  # download_torrents.py
pandas = "*"          # demo_parse_datetime.py
pandas-stubs = "*"    # so mypy can resolve pandas
numpy = "*"           # demo_parse_datetime.py

[pypi-dependencies]
# No conda-forge build. The lint extra (flake8, flake8-bugbear, autopep8) is
# myaudit.py's requirement.
emmykit = { version = ">=0.3.4", extras = ["lint"] }

# Conda deps that only resolve on linux-64 go here. Symptom of belonging here:
# `pixi install` fails with "No candidates were found" on osx-arm64.
[target.linux-64.dependencies]

[tasks]
# `python -m <tool>` dodges a macOS shebang-resolution problem with
# pixi-installed console scripts.
test = "python -m pytest"
test-cov = "python -m pytest --cov"
lint = "python -m ruff check ."
format = "python -m ruff format ."
typecheck = "python -m mypy ."
pre-commit = "python -m pre_commit"
pre-commit-all = "python -m pre_commit run --all-files"
pre-commit-install = "python -m pre_commit install --install-hooks"
```

- [ ] **Step 3: Add `.pixi/` to `.gitignore`**

Append to `/workspace/utilities/.gitignore`:

```gitignore

# pixi environment (pixi.lock IS committed — it is what makes the env reproducible)
.pixi/
```

- [ ] **Step 4: Solve the environment**

```bash
cd /workspace/utilities && pixi install
```

Expected: succeeds, creates `pixi.lock` and `.pixi/`.

**If it fails with `No candidates were found for <pkg>`** on `osx-arm64` or `osx-64`, that package has no macOS build. Move it out of `[dependencies]` into the `[target.linux-64.dependencies]` table already present in the file, then re-run `pixi install`. The likely candidates are `pandas-stubs` and `emmykit`'s lint extra; do not guess, read the error.

- [ ] **Step 5: Confirm the lock covers all three platforms**

```bash
cd /workspace/utilities && head -5 pixi.lock
```

Expected — `pixi.lock` is format v7, whose header lists the solved platforms:

```yaml
version: 7
platforms:
- name: linux-64
- name: osx-64
- name: osx-arm64
```

The solve itself is the macOS proof — no Mac is required.

`pixi.lock` is committed, so it passes through the `check-added-large-files` hook added in Task 2. For reference, the scaffold's lock is 227 KB against that hook's 500 KB limit, and this repo's dependency set is smaller — but if a future lock ever crosses it, raise the limit rather than gitignoring the lock.

- [ ] **Step 6: Confirm the new config matches the old one**

```bash
cd /workspace/utilities && pixi run lint 2>&1 | tail -2
pixi run lint --statistics 2>&1 | tail -10
```

Expected: `Found 37 errors.`, broken down as 18 `F401`, 7 `I001`, 6 `D212`, 2 `S101`, 2 `UP035`, 1 `UP039`, 1 `W291`.

This is the guard against silent config divergence. A count near 180 means the `test_*.py` per-file-ignore did not match. Any other mismatch means the new `pyproject.toml` is not equivalent to the outer scaffold's — reconcile before anything is built on top.

Four of the seven `I001` findings are the expected first-party reclassification described under "Correction discovered during Task 1"; they are fixed in Task 1b, not here.

- [ ] **Step 7: Confirm the per-file-ignore pattern matches**

```bash
cd /workspace/utilities && pixi run python -m ruff check test_printall.py --statistics
```

Expected: `1  I001` and nothing else. That file is full of bare `assert`s and undocumented functions, so any `S101`, `D` or `ANN` finding here would mean the pattern missed. The lone `I001` is expected.

- [ ] **Step 8: Confirm mypy and pytest still pass under the local config**

```bash
cd /workspace/utilities && pixi run typecheck 2>&1 | tail -2
cd /workspace/utilities && pixi run test 2>&1 | tail -2
```

Expected: `Success: no issues found in 16 source files` and `35 passed`.

- [ ] **Step 9: Commit**

```bash
cd /workspace/utilities
git add pyproject.toml pixi.toml pixi.lock .gitignore
git commit -m "chore: add pyproject.toml and pixi.toml, ignore .pixi/

Move this repo's ruff, mypy, pytest and coverage configuration in-tree
so the rules travel with a clone instead of living in the surrounding
scaffold, and declare the dependencies that were previously recorded
only as prose in README.md.

Flat dependency table: one union of every script's needs, with each
runtime entry commented with the script that requires it. pixi.lock is
committed so the environment is reproducible.

Two settings from the scaffold are deliberately not carried over: the
mypy overrides block for tests.* never matched anything here (mypy
rejects test_* patterns and this repo's tests are flat), and mypy_path
is meaningless without a src/ layout."
```

---

### Task 1b: Regroup first-party imports in four test modules

**Goal:** Apply the four `I001` auto-fixes that Task 1's config change made mandatory, bringing the count to the 33 the rest of the plan assumes.

Added during execution — see "Correction discovered during Task 1". These are `ruff check --fix` auto-fixes with no judgement involved. This task is the sole exception to the global constraint against modifying `test_*.py`.

**Files:**
- Modify: `/workspace/utilities/test_printall.py`
- Modify: `/workspace/utilities/test_mydiff.py`
- Modify: `/workspace/utilities/test_multireplace.py`
- Modify: `/workspace/utilities/test_treeview.py`

**Acceptance Criteria:**
- [ ] `pixi run lint` → `Found 33 errors.`
- [ ] All four files show `import <sibling>` in its own block, after the third-party block
- [ ] `pixi run test` → `35 passed`
- [ ] `pixi run typecheck` → `Success: no issues found in 16 source files`
- [ ] No test file is changed other than its import block

**Verify:** `cd /workspace/utilities && pixi run lint 2>&1 | tail -2 && pixi run test 2>&1 | tail -2` → `Found 33 errors.` and `35 passed`

**Steps:**

- [ ] **Step 1: Apply the auto-fixes**

```bash
cd /workspace/utilities
pixi run python -m ruff check --fix test_printall.py test_mydiff.py test_multireplace.py test_treeview.py
```

Expected: `Found 4 errors (4 fixed, 0 remaining).`

Each file's import block goes from this shape:

```python
import emmykit as ek
import printall
import pytest
```

to this:

```python
import emmykit as ek
import pytest

import printall
```

`test_multireplace.py` and `test_treeview.py` have the same shape with `multireplace` / `treeview` in place of `printall`; `test_mydiff.py` with `mydiff`.

- [ ] **Step 2: Confirm nothing but imports moved**

```bash
cd /workspace/utilities && git diff --stat
```

Expected: four files, and the changed-line count is small — each file is one import moved plus one blank line. If any file shows a large diff, something other than the import regrouping happened; stop and investigate.

- [ ] **Step 3: Confirm the count and that the tests still pass**

```bash
cd /workspace/utilities
pixi run lint 2>&1 | tail -2          # Found 33 errors.
pixi run test 2>&1 | tail -2          # 35 passed
pixi run typecheck 2>&1 | tail -2     # Success: no issues found in 16 source files
```

- [ ] **Step 4: Commit**

```bash
cd /workspace/utilities
git add test_printall.py test_mydiff.py test_multireplace.py test_treeview.py
git commit -m "tests: style: regroup sibling-script imports as first-party

Moving the ruff config into this repo changed isort's project root.
Under /workspace/pyproject.toml, src resolved to a directory with no
printall.py, so 'import printall' was classified third-party and sorted
next to pytest. Under the in-tree config, src resolves here, where the
script does exist, so it is first-party and belongs in its own block.

Four test modules import a sibling script and are affected. These are
ruff --fix auto-fixes; no test logic changed and the suite still
reports 35 passed."
```

---

### Task 2: Pre-commit configuration and hook installation

**Goal:** Commits into `utilities/` are gated by hooks defined in `utilities/` itself, for the first time.

**Files:**
- Create: `/workspace/utilities/.pre-commit-config.yaml`

**Acceptance Criteria:**
- [ ] `.git/hooks/pre-commit` exists after `pixi run pre-commit-install`
- [ ] The commit for this task passes the whole-repo `mypy` hook
- [ ] `pixi run pre-commit run --files pyproject.toml` shows `check-toml` `Passed`

**Verify:** `cd /workspace/utilities && ls .git/hooks/pre-commit && pixi run pre-commit run --files pyproject.toml 2>&1 | rg 'check-toml|mypy'` → both `Passed`

**Steps:**

- [ ] **Step 1: Create `.pre-commit-config.yaml`**

All hooks are `local` with no remote repositories, so there is no network access at commit time and every tool is the one pinned in `pixi.lock`.

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
      # Whole-repo on every commit, deliberately: a change in printall.py can
      # break test_printall.py, and a staged-files-only run would miss it.
      - id: mypy
        name: mypy
        entry: pixi run python -m mypy .
        language: system
        types: [python]
        pass_filenames: false

      # Built-in pygrep — no remote pre-commit-hooks dep, no network.
      # Real conflict markers: `<<<<<<< <ref>` and `>>>>>>> <ref>` (with
      # trailing space) and `=======` *alone on a line*. The bare-`=======`
      # form would otherwise false-positive on pytest's `======== … ========`
      # header lines, so it is anchored with $.
      - id: check-merge-conflict
        name: check-merge-conflict
        entry: '^(<<<<<<< |>>>>>>> |={7}$)'
        language: pygrep

      # Local reimplementation of pre-commit-hooks' check-added-large-files
      # (default maxkb=500 → 500000 bytes). System bash + wc only.
      - id: check-added-large-files
        name: check-added-large-files (limit 500 KB)
        entry: 'bash -c ''max=500000; rc=0; for f in "$@"; do sz=$(wc -c < "$f"); if (( sz > max )); then echo "$f: $sz bytes exceeds limit of $max" >&2; rc=1; fi; done; exit $rc'' --'
        language: system

      # Local reimplementation of pre-commit-hooks' check-toml. tomllib is
      # stdlib in 3.11+; this repo requires 3.12+.
      - id: check-toml
        name: check-toml
        entry: 'pixi run python -c ''import sys,tomllib;[tomllib.load(open(f,"rb")) for f in sys.argv[1:]]'''
        language: system
        types: [toml]
```

- [ ] **Step 2: Install the hook**

```bash
cd /workspace/utilities && pixi run pre-commit-install
ls -l .git/hooks/pre-commit
```

Expected: `pre-commit installed at .git/hooks/pre-commit`, and the file exists. This repo had no hook installed before now.

- [ ] **Step 3: Exercise the hooks before relying on them**

```bash
cd /workspace/utilities && pixi run pre-commit run --files pyproject.toml 2>&1 | rg 'check-toml|mypy|ruff'
```

Expected: `check-toml … Passed` and `mypy … Passed`. The two ruff hooks are `types: [python]` so they report `(no files to check) Skipped` for a TOML file.

- [ ] **Step 4: Commit**

The staged file is YAML, so the ruff hooks skip it and only the whole-repo `mypy` runs — which passes, because mypy is already green across all 16 files. The repo still has 33 ruff findings at this point and that is fine: the ruff hooks see staged files only.

```bash
cd /workspace/utilities
git add .pre-commit-config.yaml
git commit -m "chore: add pre-commit config and install the hook

All hooks are local and routed through pixi run python -m <tool>, so
there is no network access at commit time and every tool is the one
pinned in pixi.lock.

ruff and ruff-format see staged files only. mypy runs whole-repo on
every commit (pass_filenames: false) because a change in one module can
break another module's tests, which a staged-files-only run would miss.

This repo had no git hook installed until now."
```

---

### Task 3: Clear `download_file.py`

**Goal:** Remove the 28 findings in `download_file.py` — 18 dead imports, both `UP035`, one `UP039`, four `D212` and two dead asserts.

**Files:**
- Modify: `/workspace/utilities/download_file.py`

**Acceptance Criteria:**
- [ ] `pixi run python -m ruff check download_file.py` → `All checks passed!`
- [ ] `pixi run lint` → `Found 5 errors.`
- [ ] `pixi run python download_file.py --help` exits 0
- [ ] `pixi run typecheck` → `Success: no issues found in 16 source files`
- [ ] No `assert` remains in the file

**Verify:** `cd /workspace/utilities && pixi run lint 2>&1 | tail -2` → `Found 5 errors.`

**Steps:**

Line numbers are as of commit `d72c7a8`. Match on the quoted text rather than the number, since earlier edits shift later lines.

- [ ] **Step 1: Replace the import block**

Lines 1–13 currently read:

```python
from __future__ import annotations

import os
import sys
import argparse
import logging
from pathlib import Path
import datetime as dt
from urllib.parse import urlparse
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Type, TypeVar, Generic, NewType, Final, TypeAlias, TextIO, BinaryIO, IO, Callable, Literal, TypedDict, Protocol

import emmykit as ek
```

Replace with:

```python
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import emmykit as ek
```

This removes all 18 `F401` findings (`dt`, `Iterable`, `Mapping`, `Sequence`, and the 14 `typing` names) and both `UP035` findings, which sit on the same `typing` line. It also fixes `I001` by sorting the remaining stdlib imports. Every removed name is unreferenced in the file — `os`, `sys`, `argparse`, `logging`, `Path` and `urlparse` are all still used.

- [ ] **Step 2: Drop the empty parentheses on the class (`UP039`)**

```python
# before
class Options():

# after
class Options:
```

- [ ] **Step 3: Delete both dead asserts (`S101`)**

`self.args` is declared `argparse.Namespace`, never `Optional`, so these narrow nothing for mypy and guard nothing at runtime — under `python -O` they would not exist at all. Delete, do not convert to `raise`.

In `parse_arguments()`, delete the middle line:

```python
    options.args = parser.parse_args()
    assert options.args is not None          # <- delete this line
    if options.args.debug:
```

In `run_download()`, delete the assert and the blank line that follows it:

```python
        SystemExit: Propagated if emmykit.download_file() exits on error.
    """
    assert options.args is not None          # <- delete this line
                                             # <- and this blank line
    url: str = options.args.url
```

leaving:

```python
        SystemExit: Propagated if emmykit.download_file() exits on error.
    """
    url: str = options.args.url
```

- [ ] **Step 4: Move all four docstring summaries onto the opening line (`D212`)**

`parse_arguments()`:

```python
# before
    """
    Parse command-line arguments.

    Args:

# after
    """Parse command-line arguments.

    Args:
```

`determine_destination_path()`:

```python
# before
    """
    Determine the destination path for a download based on the URL.

    Args:

# after
    """Determine the destination path for a download based on the URL.

    Args:
```

`run_download()`:

```python
# before
    """
    Perform the download based on parsed command-line options.

    Args:

# after
    """Perform the download based on parsed command-line options.

    Args:
```

`main()`:

```python
# before
    """
    Main function.

    Args:

# after
    """Main function.

    Args:
```

Only the first two lines of each docstring change. Leave the `Args:` / `Returns:` / `Raises:` bodies untouched.

- [ ] **Step 5: Verify the file is clean, then format it**

```bash
cd /workspace/utilities
pixi run python -m ruff check download_file.py
pixi run python -m ruff format download_file.py
pixi run python -m ruff check download_file.py
```

Expected: `All checks passed!`, then `1 file reformatted`, then `All checks passed!` again.

The formatter reflows the long `parser.add_argument(...)` calls. It produces **no** `= (` wraps in the `Options` block — verified against the real file — so no comment repositioning is needed here.

- [ ] **Step 6: Verify the script still imports and runs**

Deleting imports can only break a script at import time, so `--help` is the meaningful check.

```bash
cd /workspace/utilities && pixi run python download_file.py --help; echo "rc=$?"
```

Expected: usage text, `rc=0`.

- [ ] **Step 7: Confirm the running count and that nothing else regressed**

```bash
cd /workspace/utilities
pixi run lint 2>&1 | tail -2          # Found 5 errors.
pixi run typecheck 2>&1 | tail -2     # Success: no issues found in 16 source files
pixi run test 2>&1 | tail -2          # 35 passed
rg -c '\bassert\b' download_file.py   # no matches
```

- [ ] **Step 8: Commit**

```bash
cd /workspace/utilities
git add download_file.py
git commit -m "download_file.py: refactor: drop dead imports and asserts

Removes 28 of the repo's 33 ruff findings, all from three root causes.

The pasted kitchen-sink typing import plus two stray imports accounted
for 18 F401 findings and both UP035 findings, since typing.Type and
Callable sat on that same line. None of the 18 names was referenced.

The two 'assert options.args is not None' statements are deleted rather
than converted to raises: self.args is declared argparse.Namespace and
is never Optional, so they narrow nothing for mypy and guard nothing at
runtime, and under python -O they would not exist at all.

Also drops the empty parentheses on class Options and moves four
docstring summaries onto their opening line."
```

---

### Task 4: Clear `check_internet.py`

**Goal:** Remove the 3 findings in `check_internet.py` — one import-order and two docstring-placement.

**Files:**
- Modify: `/workspace/utilities/check_internet.py`

**Acceptance Criteria:**
- [ ] `pixi run python -m ruff check check_internet.py` → `All checks passed!`
- [ ] `pixi run lint` → `Found 2 errors.`
- [ ] `pixi run python check_internet.py --help` exits 0

**Verify:** `cd /workspace/utilities && pixi run lint 2>&1 | tail -2` → `Found 2 errors.`

**Steps:**

- [ ] **Step 1: Sort the imports (`I001`)**

Lines 1–8 currently read:

```python
from __future__ import annotations

import sys
import argparse
import logging
from pathlib import Path

import emmykit as ek
```

Replace with:

```python
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import emmykit as ek
```

- [ ] **Step 2: Move both docstring summaries onto the opening line (`D212`)**

`parse_arguments()`:

```python
# before
    """
    Parse command-line arguments.

    Args:

# after
    """Parse command-line arguments.

    Args:
```

`main()`:

```python
# before
    """
    Main function.

    Args:

# after
    """Main function.

    Args:
```

Leave the `Args:` / `Returns:` / `Raises:` bodies untouched.

- [ ] **Step 3: Verify clean, then format**

```bash
cd /workspace/utilities
pixi run python -m ruff check check_internet.py
pixi run python -m ruff format check_internet.py
pixi run python -m ruff check check_internet.py
```

Expected: `All checks passed!`, `1 file reformatted`, `All checks passed!`.

Like `download_file.py`, this file produces no `= (` wraps — its `Options` block, including the aligned block of tunable defaults, collapses to lines under 88 characters. Verified against the real file.

- [ ] **Step 4: Verify the script still runs**

```bash
cd /workspace/utilities && pixi run python check_internet.py --help; echo "rc=$?"
```

Expected: usage text, `rc=0`. Do not run it without `--help` — it makes real network calls and sets its exit code from the result.

- [ ] **Step 5: Confirm the running count**

```bash
cd /workspace/utilities
pixi run lint 2>&1 | tail -2       # Found 2 errors.
pixi run typecheck 2>&1 | tail -2  # Success: no issues found in 16 source files
pixi run test 2>&1 | tail -2       # 35 passed
```

- [ ] **Step 6: Commit**

```bash
cd /workspace/utilities
git add check_internet.py
git commit -m "check_internet.py: docs: fix docstring summary placement and import order

Sorts the stdlib imports and moves the parse_arguments() and main()
docstring summaries onto their opening line, per the Google convention
this repo's ruff config selects. No behaviour change."
```

---

### Task 5: Demote `test_parse_datetime.py` to a demo

**Goal:** Stop a file that asserts nothing from masquerading as a test, and clear its 2 findings.

`test_parse_datetime.py` is 157 lines containing 72 top-level `print()` calls, zero test functions and zero live assertions — its five `assert` lines, at 153–157, are commented out. pytest imports it at collection, runs every print, and collects nothing. It exercises `ek.parse_datetime` and `ek.parse_timezone`, which no script in this repo calls.

**Files:**
- Rename: `/workspace/utilities/test_parse_datetime.py` → `/workspace/utilities/demo_parse_datetime.py`
- Modify: `/workspace/utilities/demo_parse_datetime.py`

**Acceptance Criteria:**
- [ ] `test_parse_datetime.py` no longer exists; `demo_parse_datetime.py` does, with history preserved via `git mv`
- [ ] `pixi run python -m ruff check demo_parse_datetime.py` → `All checks passed!`
- [ ] `pixi run lint` → `All checks passed!` (0 findings, down from 33)
- [ ] `pixi run test` still reports `35 passed`
- [ ] The four repositioned comments are preserved verbatim, just moved above their statements
- [ ] Lines 153–157's commented-out assertions are left untouched

**Verify:** `cd /workspace/utilities && pixi run lint 2>&1 | tail -2 && pixi run test 2>&1 | tail -2` → `All checks passed!` and `35 passed`

**Steps:**

- [ ] **Step 1: Rename with history**

```bash
cd /workspace/utilities && git mv test_parse_datetime.py demo_parse_datetime.py
```

The `demo_` prefix takes it out of pytest's collection path. It is not covered by the `test_*.py` per-file-ignore any more, which is fine: linting it under the full rule set produces only the two findings below, because its five `assert` lines are commented out and it defines no functions.

- [ ] **Step 2: Sort the imports (`I001`)**

Lines 1–5 currently read:

```python
import datetime as dt
import numpy as np
import pandas as pd

import emmykit as ek
```

Replace with:

```python
import datetime as dt

import emmykit as ek
import numpy as np
import pandas as pd
```

`datetime` is stdlib; `emmykit`, `numpy` and `pandas` are third-party and sort alphabetically.

- [ ] **Step 3: Strip the trailing space on line 110 (`W291`)**

```python
# before — note the single trailing space after "Date"
print(f"{ek.parse_datetime('JD 2459396.5') = }")  # Julian Date 

# after
print(f"{ek.parse_datetime('JD 2459396.5') = }")  # Julian Date
```

- [ ] **Step 4: Move four long trailing comments above their statements**

These four lines are the only ones `ruff format` would break into three lines, because the trailing comment pushes them past 88 characters. This file's value is one scannable line per example, so move the comment above instead of accepting the wrap. Verified: exactly four lines are affected.

Line 111:

```python
# before
print(f"{ek.parse_datetime('2459396.5', format_str='JD') = }")  # Julian Date without prefix

# after
# Julian Date without prefix
print(f"{ek.parse_datetime('2459396.5', format_str='JD') = }")
```

Line 117:

```python
# before
print(f"{ek.parse_datetime('J2000') = }")  # J2000 epoch → January 1, 2000, 11:58:55.816 UTC

# after
# J2000 epoch → January 1, 2000, 11:58:55.816 UTC
print(f"{ek.parse_datetime('J2000') = }")
```

Line 120:

```python
# before
print(f"{ek.parse_datetime('UNIX', timezone='AWST') = }")  # Unix epoch in Western Australia Standard Time

# after
# Unix epoch in Western Australia Standard Time
print(f"{ek.parse_datetime('UNIX', timezone='AWST') = }")
```

Line 129:

```python
# before
print(f"{ek.parse_datetime(not_naive, timezone='naive') = }")  # Convert to naive datetime

# after
# Convert to naive datetime
print(f"{ek.parse_datetime(not_naive, timezone='naive') = }")
```

Leave every other trailing comment alone. The other 19 lines the formatter touches merely lose their alignment padding, which is the intended outcome of the format decision.

- [ ] **Step 5: Leave lines 153–157 untouched**

```python
# assert parse_datetime('JD 2459396.5') == datetime(2021, 3, 31, 0, 0, tzinfo=timezone.utc)
# assert parse_datetime('MJD 59396.0') == datetime(2021, 3, 31, 0, 0, tzinfo=timezone.utc)
# assert parse_datetime('2025-176') == datetime(2025, 6, 25, tzinfo=timezone.utc)
# assert parse_datetime('44 BC')   # → year =  -43  → Jan 1 –0043 (or via Astropy)
# assert parse_datetime('37 CE')   # → year =   37  → Jan 1 0037
```

These are the only genuinely test-shaped content in the file, and the expected values are hand-derived rather than produced by running the code. They are the seed if real coverage of those parsers is ever wanted. This plan does not act on them.

- [ ] **Step 6: Verify clean, then format**

```bash
cd /workspace/utilities
pixi run python -m ruff check demo_parse_datetime.py
pixi run python -m ruff format demo_parse_datetime.py
pixi run python -m ruff check demo_parse_datetime.py
rg -c '^print\($' demo_parse_datetime.py
```

Expected: `All checks passed!`, `1 file reformatted`, `All checks passed!`, and **no matches** for `^print($` — a bare `print(` on its own line would mean a wrap survived and a fifth long comment was missed.

- [ ] **Step 7: Confirm the demo still runs, and that the test count is unchanged**

```bash
cd /workspace/utilities && pixi run python demo_parse_datetime.py > /dev/null; echo "rc=$?"
pixi run test 2>&1 | tail -2
pixi run lint 2>&1 | tail -2
pixi run typecheck 2>&1 | tail -2
```

Expected: `rc=0`; `35 passed`; `All checks passed!`; `Success: no issues found in 16 source files`.

**`35 passed` is the point of this task.** It is the falsifiable form of the claim that this file was never a test: if the count moves off 35, the file was contributing tests after all and the demotion is wrong. Stop and reconsider rather than adjusting the number.

- [ ] **Step 8: Commit**

```bash
cd /workspace/utilities
git add -A demo_parse_datetime.py test_parse_datetime.py
git commit -m "test_parse_datetime.py: refactor: demote to demo_parse_datetime.py

This file was never a test. 157 lines, 72 top-level print() calls, zero
test functions and zero live assertions (its five assert lines are
commented out). pytest imported it at collection, ran every print, and
collected nothing. The suite reports 35 passed both before and after
this rename.

It also exercises ek.parse_datetime and ek.parse_timezone, which no
script in this repo calls.

Not converted to real assertions: only 12 of its 72 lines record an
expected value, so the other 60 would have to be filled in by running
the current emmykit and recording whatever it produced, which would
lock in today's behaviour including any bugs.

Four long trailing comments moved above their statements so ruff format
leaves the one-line-per-example layout intact. The commented-out
assertions at the end are left as-is; their expected values are
hand-derived and are the seed if real coverage is ever wanted."
```

---

### Task 6: Format the remaining file

**Goal:** Every file in the repo is ruff-formatted, making `pre-commit run --all-files` reachable.

Tasks 3, 4 and 5 each staged a file, and the `ruff-format` hook formats staged files, so `detect_country.py` is the only unformatted file left.

**Files:**
- Modify: `/workspace/utilities/detect_country.py`

**Acceptance Criteria:**
- [ ] `pixi run format` reports every file already formatted on a second run (idempotent)
- [ ] `pixi run lint` → `All checks passed!`
- [ ] `pixi run test` → `35 passed`

**Verify:** `cd /workspace/utilities && pixi run format --check 2>&1 | tail -1` → `16 files already formatted`

Note: `pixi run format --check` works because pixi forwards trailing arguments, making it `ruff format . --check`. The count is 16 here and becomes 17 once Task 7 adds `_template.py`.

**Steps:**

- [ ] **Step 1: Format the repo**

```bash
cd /workspace/utilities && pixi run format
```

Expected: `1 file reformatted, 15 files left unchanged` — the reformatted one being `detect_country.py`, whose only change is reflowing this call:

```python
# before
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")

# after
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
```

If more than one file is reformatted, an earlier task skipped its format step. Check which, and confirm it was not one of the five adopted scripts, which are already formatted and must not change.

- [ ] **Step 2: Confirm idempotence and that nothing regressed**

```bash
cd /workspace/utilities
pixi run format 2>&1 | tail -1        # 16 files left unchanged
pixi run lint 2>&1 | tail -2          # All checks passed!
pixi run typecheck 2>&1 | tail -2     # Success: no issues found in 16 source files
pixi run test 2>&1 | tail -2          # 35 passed
```

- [ ] **Step 3: Commit**

```bash
cd /workspace/utilities
git add detect_country.py
git commit -m "detect_country.py: chore: format with ruff format

Completes the one-off repo-wide format. Every other file was formatted
as it was staged in the preceding commits, so this is the last one.

The hand-aligned annotation columns this repo used are deliberately
abandoned: they are incompatible with ruff format, and keeping the
formatter means every future diff is clean and pre-commit run
--all-files is reachable."
```

---

### Task 7: Add `_template.py`

**Goal:** New scripts start from a clean skeleton, so the boilerplate debt just removed cannot regenerate.

**Files:**
- Create: `/workspace/utilities/_template.py`

**Acceptance Criteria:**
- [ ] `pixi run python -m ruff check _template.py` → `All checks passed!`
- [ ] `pixi run typecheck` → `Success: no issues found in 17 source files`
- [ ] `pixi run python _template.py --help` exits 0
- [ ] `pixi run python _template.py` exits 0 and logs one line
- [ ] `pixi run test` still reports `35 passed` — the leading underscore keeps pytest from collecting it
- [ ] The file contains no `import emmykit`

**Verify:** `cd /workspace/utilities && pixi run python _template.py --help > /dev/null && pixi run python -m ruff check _template.py` → exit 0 and `All checks passed!`

**Steps:**

- [ ] **Step 1: Create `_template.py`**

The leading underscore keeps pytest from collecting it, keeps coverage from measuring it (it is in the `omit` list from Task 1), and sorts it to the top of a directory listing.

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


def parse_arguments(options: Options) -> None:
    """Parse command-line arguments.

    Args:
        options: Options object whose ``args`` and ``log_mode`` are updated in place.

    Returns:
        None, but updates options.args with parsed arguments.

    Raises:
        SystemExit: If the '-v'/'--version' flag is provided (prints and exits).
    """
    parser = argparse.ArgumentParser(description="One-line description of the script.")
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-debug", "--debug", action="store_true", help="Enable DEBUG logging."
    )
    options.args = parser.parse_args()
    if options.args.debug:
        options.log_mode = logging.DEBUG


def main() -> None:
    """Describe here what this script does."""
    options: Options = Options()
    parse_arguments(options)
    logging.basicConfig(
        level=options.log_mode,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.info("Replace this with the real work of %s.", options.my_name)
    logging.shutdown()


if __name__ == "__main__":
    main()
```

The emmykit line is a **comment, not an import**. A speculative `import emmykit as ek` would be flagged `F401` — the template would ship the exact defect it exists to prevent.

- [ ] **Step 2: Verify it passes its own repo's rules**

```bash
cd /workspace/utilities
pixi run python -m ruff check _template.py       # All checks passed!
pixi run python -m ruff format --check _template.py
pixi run typecheck 2>&1 | tail -2                # 17 source files
```

- [ ] **Step 3: Verify it actually runs**

```bash
cd /workspace/utilities
pixi run python _template.py --help; echo "rc=$?"
pixi run python _template.py; echo "rc=$?"
pixi run python _template.py --version; echo "rc=$?"
```

Expected: usage text with `rc=0`; one `INFO` line ending `Replace this with the real work of _template.` with `rc=0`; `_template.py 0.1.0` with `rc=0`.

- [ ] **Step 4: Verify pytest ignores it**

```bash
cd /workspace/utilities && pixi run test 2>&1 | tail -2
```

Expected: `35 passed` — unchanged.

- [ ] **Step 5: Commit**

```bash
cd /workspace/utilities
git add _template.py
git commit -m "_template.py: feat: add a clean starting point for new scripts

The kitchen-sink typing import removed from download_file.py was a
paste artifact, so fixing it once would not stop the next script
carrying it. This encodes the repo's actual shape instead: __version__,
an Options class, parse_arguments() with the -v/-debug pair, main(),
and the __main__ guard.

The leading underscore keeps pytest from collecting it and coverage
from measuring it. It is a real linted file, so it cannot silently rot.

The emmykit line is a comment rather than an import: a speculative
import emmykit as ek would be F401, which would make the template ship
the exact defect it exists to prevent."
```

---

### Task 8: Update the documentation

**Goal:** `README.md` and `CLAUDE.md` describe the repo as it now is, and record the conventions that keep it clean.

**Files:**
- Modify: `/workspace/utilities/README.md`
- Modify: `/workspace/utilities/CLAUDE.md`

**Acceptance Criteria:**
- [ ] `rg 'test_parse_datetime' -g '!docs/**' -g '!.git/**'` returns no matches
- [ ] `README.md`'s structure table lists `_template.py`, `demo_parse_datetime.py` and `docs/`
- [ ] `CLAUDE.md` documents running tools from this directory, the `_template.py` convention, and the `test_*` / `demo_*` naming rule
- [ ] `pixi run pre-commit-all` → every hook `Passed`

**Verify:** `cd /workspace/utilities && pixi run pre-commit-all 2>&1 | rg -c 'Passed'` → 6

**Steps:**

- [ ] **Step 1: Update `README.md`'s installation section**

Replace the opening of the Installation section with a pixi path alongside the existing pip path:

```markdown
## Installation

For development in this repository, everything is pinned in `pixi.toml`:

```bash
pixi install
```

To run a single script standalone, outside this repo, it needs Python 3.12+
and `emmykit`:

```bash
pip install 'emmykit>=0.3.4'
```
```

Leave the existing `emmykit[lint]` and `requests beautifulsoup4` paragraphs as they are — they still describe what a standalone user needs.

- [ ] **Step 2: Update `README.md`'s structure table**

Add three rows to the existing table, keeping it alphabetical, and note `docs/`:

```markdown
| `_template.py` | Starting point for a new script — copy, rename, fill in |
| `demo_parse_datetime.py` | Runnable examples of `emmykit`'s datetime parsers (prints, no assertions) |
```

and after the table:

```markdown
Naming rules, enforced by convention rather than by tooling:

- `test_*.py` — real pytest modules with assertions. Collected by `pixi run test`.
- `demo_*.py` — runnable examples that print. Not collected, not covered.
- `_template.py` — the skeleton for new scripts. Not collected, not covered.

`docs/superpowers/` holds the design specs and implementation plans for
larger changes.
```

Replace the existing line `Tests live alongside the scripts as `test_<script>.py` and run with `pytest`.` with those rules, so the information is stated once.

- [ ] **Step 3: Add a tooling section to `CLAUDE.md`**

Append to `/workspace/utilities/CLAUDE.md`:

```markdown
## Tooling

This repository is self-governing: `pyproject.toml`, `pixi.toml`, `pixi.lock`
and `.pre-commit-config.yaml` all live here. Run every tool from this
directory, not from a parent — `pixi run` resolves the manifest here.

- `pixi install` — create or update the environment
- `pixi run test` — pytest
- `pixi run lint` — `ruff check .`
- `pixi run format` — `ruff format .`
- `pixi run typecheck` — `mypy .` (strict)
- `pixi run pre-commit-all` — every hook over every file
- `pixi run pre-commit-install` — wire `.git/hooks/pre-commit`

The `ruff` hook runs with `--fix` and the `ruff-format` hook rewrites files,
so a failed commit often means the hooks *changed* your staged files rather
than that something is broken. Re-add and commit again. The `mypy` hook runs
over the whole repository on every commit, not just staged files.

## Conventions for new scripts

Start from `_template.py`. It carries the shape every script here uses:
`from __future__ import annotations`, a `__version__` string, an `Options`
class holding the globals, `parse_arguments()`, `main()`, and the
`if __name__ == "__main__":` guard.

Do not paste a speculative `from typing import ...` line. Import what the
script uses; `F401` will reject the rest.

File naming:

- `test_*.py` — real pytest modules with assertions
- `demo_*.py` — runnable examples that print rather than assert
- `_template.py` — the skeleton, collected by nothing
```

- [ ] **Step 4: Confirm no stale references survive**

```bash
cd /workspace/utilities && rg 'test_parse_datetime' -g '!docs/**' -g '!.git/**'; echo "exit=$?"
```

Expected: `exit=1` (no matches). Matches inside `docs/` are the spec and this plan describing the rename, and are correct.

- [ ] **Step 5: Run the full acceptance check**

```bash
cd /workspace/utilities
pixi run lint 2>&1 | tail -2            # All checks passed!
pixi run format --check 2>&1 | tail -1  # 17 files already formatted
pixi run typecheck 2>&1 | tail -2       # Success: no issues found in 17 source files
pixi run test 2>&1 | tail -2            # 35 passed
pixi run pre-commit-all 2>&1 | rg 'Passed|Failed'
```

Expected from the last command: six `Passed` lines and no `Failed`. **This is the deliverable** — `pre-commit run --all-files` has never been green for this repository before.

- [ ] **Step 6: Commit**

```bash
cd /workspace/utilities
git add README.md CLAUDE.md
git commit -m "docs: update README and CLAUDE.md for the new layout

README gains the pixi install path, the _template.py and
demo_parse_datetime.py entries, the docs/ directory, and the test_ /
demo_ / _template naming rules.

CLAUDE.md gains a tooling section — run everything from this directory
now that the config lives here, and expect the ruff hooks to rewrite
staged files — plus the conventions for starting a new script from
_template.py rather than pasting a speculative typing import."
```

- [ ] **Step 7 (optional, different repository): exclude `utilities/` from the outer scaffold**

`/workspace` still lints `utilities/` under its own rules, which is a second source of truth that can drift. Add to `/workspace/pyproject.toml`:

```toml
[tool.ruff]
extend-exclude = ["utilities"]

[tool.mypy]
exclude = ["^utilities/"]
```

This is hygiene, not a guarantee — the scaffold is regenerated, which would drop the exclusion. The real guarantee is running tools from inside `utilities/`, which the new `[tasks]` make the natural thing to do. Do not commit this in the `utilities` repo; it belongs to `/workspace`.

---

## Rollback

Every task is one commit, so `git revert <sha>` undoes any single step. Task 1 is the only one that touches the environment: reverting it leaves a stale `.pixi/` directory, which is gitignored and safe to `rm -rf`.

If Task 1's finding count comes out wrong and cannot be reconciled, stop. The whole plan depends on the local config being equivalent to the one the 33 findings were measured under.
