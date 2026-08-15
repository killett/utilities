from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from pathlib import Path

import emmykit as ek

__version__: str = "0.1.0"

# ek.interactive_flake8() imports flake8/autopep8 lazily and ek.run_mypy() imports
# mypy lazily, so a missing tool surfaces as a bare ModuleNotFoundError deep inside
# emmykit. Check up front instead and say what to install.
REQUIRED_MODULES: tuple[str, ...] = ("flake8", "autopep8", "mypy")
INSTALL_HINT: str = "Install them with: pip install 'emmykit[lint]' mypy"


class Options(ek.Options):
    """Class that has all global options in one place.

    Subclasses ``emmykit.Options`` because ``ek.interactive_flake8()`` and
    ``ek.run_mypy()`` take an ``emmykit.Options``, and ``ek.run_flake8()``
    writes the detected bugbear setting back onto ``bugbear_choice``.
    """

    def __init__(self) -> None:
        """Initialize the Options class with default values."""
        super().__init__()
        # The invoked name of this script, without the .py extension.
        self.my_name: str = Path(sys.argv[0]).stem
        # Use the -debug command line argument to change to DEBUG.
        self.log_mode: int = logging.INFO
        # Default to the current working directory.
        self.default_dir: Path = Path.cwd().expanduser().resolve(strict=True)


def missing_lint_tooling(modules: tuple[str, ...]) -> list[str]:
    """Return the names of the required lint modules that are not importable.

    Args:
        modules: Module names to probe, normally REQUIRED_MODULES.

    Returns:
        The subset of ``modules`` that cannot be imported, in the given order.
    """
    return [name for name in modules if importlib.util.find_spec(name) is None]


def parse_arguments(options: Options) -> None:
    """Parse command-line arguments.

    Args:
        options: Options object whose ``args`` and ``log_mode`` are updated in place.

    Returns:
        None, but updates options.args with parsed arguments.

    Raises:
        SystemExit: If the '-v'/'--version' flag is provided (prints and exits).
    """
    parser = argparse.ArgumentParser(description="Check Python formatting in a file.")
    parser.add_argument("filepath", type=Path, help="Path to the Python file to check")
    parser.add_argument(
        "--diff_choice",
        type=int,
        default=1,
        help="0 = old-style diff, 1 = unified diff with 0 context lines, "
        "2+ = unified diff with 'diff_choice - 1' context lines",
    )
    parser.add_argument(
        "--changed_color",
        type=str,
        default=ek.ANSI_CYAN,
        help="Color for unchanged characters in changed lines (default: ANSI_CYAN)",
    )
    parser.add_argument(
        "--deleted_color",
        type=str,
        default=ek.ANSI_RED,
        help="Color for deleted characters in original lines (default: ANSI_RED)",
    )
    parser.add_argument(
        "--added_color",
        type=str,
        default=ek.ANSI_GREEN,
        help="Color for added characters in changed lines (default: ANSI_GREEN)",
    )
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
    """Audit one Python file with flake8, autopep8 and mypy."""
    options: Options = Options()
    parse_arguments(options)
    memory_handler = ek.configure_logging(
        options.my_name, log_level=options.log_mode, rawlog=True
    )
    missing = missing_lint_tooling(REQUIRED_MODULES)
    if missing:
        logging.error(
            "Missing linting tool(s): %s. %s", ", ".join(missing), INSTALL_HINT
        )
        logging.shutdown()
        sys.exit(2)
    if not ek.check_python_formatting(
        options.args.filepath, diff_choice=options.args.diff_choice
    ):
        return
    ek.interactive_flake8(
        options,
        options.args.filepath,
        diff_choice=options.args.diff_choice,
        ignore_codes=ek.IGNORED_CODES,
        max_line_length=1000,
        changed_color=options.args.changed_color,
        deleted_color=options.args.deleted_color,
        added_color=options.args.added_color,
    )
    ek.run_mypy(options, options.args.filepath)
    if memory_handler is not None:
        ek.print_all_errors(memory_handler)
    logging.shutdown()


if __name__ == "__main__":
    main()
