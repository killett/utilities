# Project: utilities

A collection of independent standalone scripts (one utility per file).

## Commit message convention

This repo holds multiple unrelated scripts, so commit messages must
identify which script they concern. Prefix the usual Conventional
Commit message with the name of the script the commit works on,
followed by `: `:

```
<script-name>: <type>: <description>
```

where `<type>` is the normal Conventional Commit type (`feat`, `fix`,
`chore`, `test`, `docs`, `refactor`, etc.). Examples:

- `clean-caches.sh: feat: add rehash hint after install`
- `download_file.py: chore: bump default timeout`
- `check_internet.py: fix: handle IPv6-only hosts`

Use the exact filename (including extension) as the prefix. A commit
that spans no single script (repo-wide config, licensing, etc.) may
omit the script prefix and use a bare `<type>: <description>`.

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
over the whole repository on every commit that touches Python, not just the
staged files.

`ruff format` rewrites ```python blocks inside Markdown, which would destroy
the deliberately-unformatted "before" examples in `docs/`. `*.md` is therefore
excluded in `[tool.ruff.format]`.

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
