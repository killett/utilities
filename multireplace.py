from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import emmykit as ek

__version__: str = "0.1.0"


class Options(ek.Options):
    """Class that has all global options in one place.

    Subclasses ``emmykit.Options`` because ``ek.multireplace()`` takes an
    ``emmykit.Options`` and reads the parsed arguments off its ``args``.
    """

    def __init__(self) -> None:
        """Initialize the Options class with default values."""
        super().__init__()
        # The invoked name of this script, without the .py extension.
        self.my_name: str = Path(sys.argv[0]).stem
        # Use the -debug command line argument to change to DEBUG.
        self.log_mode: int = logging.INFO
        self.default_glob_pattern: str = "*"
        # Default to the current working directory.
        self.default_dir: Path = Path.cwd().expanduser().resolve(strict=True)


def parse_arguments(options: Options) -> None:
    """Parse command-line arguments.

    Args:
        options: Options object whose ``args`` and ``log_mode`` are updated in place.

    Returns:
        None, but updates options.args with parsed arguments.

    Raises:
        SystemExit: If the '-v'/'--version' flag is provided (prints and exits).
    """
    parser = argparse.ArgumentParser(
        description="Find files by glob and call ek.ask_and_replace() on each until it returns False."
    )
    parser.add_argument("old_str", help="The text to be replaced in the files.")
    parser.add_argument("new_str", help="The text to replace the old_str.")
    parser.add_argument(
        "glob_pattern",
        nargs="?",
        default=options.default_glob_pattern,
        metavar="GLOB",
        help=f'Glob pattern of files to edit (default: "{options.default_glob_pattern}"). Example: "*.py"',
    )
    parser.add_argument(
        "--dir",
        "-d",
        type=Path,
        default=options.default_dir,
        metavar="DIR",
        help=f"Directory to search in (defaults to current working directory: {options.default_dir}).",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Search recursively in subdirectories.",
    )
    parser.add_argument(
        "--verbose",
        "-V",
        action="store_true",
        help="Log messages about files with no occurrences found.",
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
    """Run an interactive find/replace over every file matching the glob."""
    options: Options = Options()
    parse_arguments(options)
    memory_handler = ek.configure_logging(
        options.my_name, log_level=options.log_mode, rawlog=True
    )
    ek.multireplace(options, verbose=options.args.verbose)
    if memory_handler is not None:
        ek.print_all_errors(memory_handler)
    logging.shutdown()


if __name__ == "__main__":
    main()
