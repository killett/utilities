#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

import emmykit as ek

__version__: str = "0.1.1"


class Options:
    """Class that has all global options in one place."""

    def __init__(self) -> None:
        """Initialize the Options class with default values."""
        # The invoked name of this script, without the .py extension.
        self.my_name: str = Path(sys.argv[0]).stem
        self.default_exclude_dirs: set[str] = set(ek.DEFAULT_EXCLUDE_DIRS)
        # Default to the current working directory.
        self.default_dir: Path = Path.cwd().expanduser().resolve(strict=True)
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
    parser = argparse.ArgumentParser(
        description="Print a tree view of the specified directory."
    )
    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=options.default_dir,
        help=f"Directory to search in (defaults to current working directory: {options.default_dir}).",
    )
    parser.add_argument(
        "--no-colors", action="store_true", help="Do not use colors in the output."
    )
    parser.add_argument(
        "--exclude-dirs",
        action="extend",
        nargs="+",
        default=None,
        help=f"Directory name to exclude (can be given multiple times). Any directories given will be added to the default set: {sorted(options.default_exclude_dirs)}",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-debug", "--debug", action="store_true", help="Enable DEBUG logging."
    )
    options.args = parser.parse_args()
    options.args.exclude_dirs = set(ek.DEFAULT_EXCLUDE_DIRS) | set(
        options.args.exclude_dirs or []
    )
    if options.args.debug:
        options.log_mode = logging.DEBUG


def main() -> None:
    """Print a tree view of the requested directory."""
    options: Options = Options()
    parse_arguments(options)
    memory_handler = ek.configure_logging(
        options.my_name, log_level=options.log_mode, rawlog=True
    )
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug("Directory: %s", options.args.directory)
    state: dict[str, Any] = {
        "excluded_dirs": options.args.exclude_dirs,
        "already_printed": set(),
        "my_filepath": Path(__file__).expanduser().resolve(),
    }
    ek.treeview_new_files(
        options.args.directory, use_colors=not options.args.no_colors, state=state
    )
    if memory_handler is not None:
        ek.print_all_errors(memory_handler)
    logging.shutdown()


if __name__ == "__main__":
    main()
