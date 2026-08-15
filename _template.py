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
        # emmykit installs a root handler at import time, which makes a
        # plain basicConfig() a silent no-op -- level and format both ignored.
        force=True,
    )
    logging.info("Replace this with the real work of %s.", options.my_name)
    logging.shutdown()


if __name__ == "__main__":
    main()
