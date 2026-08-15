# utilities

General use python scripts. Most of them import
[`emmykit`](https://github.com/killett/emmykit). Each file is an independent
standalone program with its own `argparse` interface and
`if __name__ == "__main__":` block — there is no package to install and no
shared entry point. Run one with `python <script>`.

## Installation

For development in this repository, everything is pinned in `pixi.toml` and
`pixi.lock`:

```bash
pixi install
```

To run a single script standalone, outside this repo, it needs Python 3.12+
and `emmykit`:

```bash
pip install 'emmykit>=0.3.4'
```

`myaudit.py` additionally shells out to flake8, autopep8 and mypy through
`emmykit`. Without them it exits 2 with a message naming what is missing:

```bash
pip install 'emmykit[lint]' mypy
```

`flake8-bugbear` comes with `emmykit[lint]`. It is optional — `myaudit.py`
runs without it and just skips the bugbear checks.

`download_torrents.py` needs `requests` and `beautifulsoup4`:

```bash
pip install requests beautifulsoup4
```

The five adopted scripts — `printall.py`, `mydiff.py`, `myaudit.py`,
`multireplace.py` and `treeview.py` — need nothing beyond the `emmykit` base
install, apart from `myaudit.py`'s lint tooling above.

## Quick usage

```bash
python check_internet.py --strict
python printall.py src/ -p my_function -r -n
python mydiff.py old.txt new.txt
python treeview.py ~/projects --no-colors
python multireplace.py old_name new_name '*.py' --dir src --recursive
python myaudit.py some_module.py
```

Every script with an `argparse` interface supports `--help`, `-v`/`--version`
and `-debug`.

## Project structure

| Script | What it does |
| --- | --- |
| `check_internet.py` | Check internet availability using several strategies |
| `detect_country.py` | Report the country the machine appears to be in |
| `download_file.py` | Download a file from a URL |
| `download_torrents.py` | Scrape `.torrent` links from a page and fetch them |
| `multireplace.py` | Find files by glob and run an interactive find/replace on each |
| `myaudit.py` | Check Python formatting: flake8, mypy, interactive autopep8 |
| `mydiff.py` | Diff two files using `emmykit`'s `my_diff()` |
| `printall.py` | Search Python files and print full logical statements matching a pattern |
| `treeview.py` | Print a tree view of a directory |
| `clean-caches.sh` | Clear `__pycache__` directories and virtualenv caches |
| `_template.py` | Starting point for a new script — copy, rename, fill in |
| `demo_parse_datetime.py` | Runnable examples of `emmykit`'s datetime parsers (prints, no assertions) |

Naming rules, enforced by convention rather than by tooling:

- `test_*.py` — real pytest modules with assertions. Collected by `pixi run test`.
- `demo_*.py` — runnable examples that print. Not collected, not covered.
- `_template.py` — the skeleton for new scripts. Not collected, not covered.

`docs/superpowers/` holds the design specs and implementation plans for larger
changes.

Scripts that use `emmykit`'s `configure_logging()` — `multireplace.py`,
`myaudit.py`, `mydiff.py` and `treeview.py` — write a `logs/` directory into
the current working directory. It is gitignored.
