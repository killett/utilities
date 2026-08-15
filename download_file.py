from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import emmykit as ek

__version__: str = "0.1.0"


class Options:
    """Class that has all global options in one place."""

    def __init__(self) -> None:
        """Initialize the Options class with default values."""
        self.my_name: str = Path(sys.argv[0]).stem
        self.default_dest_dir: Path = Path.cwd().expanduser().resolve()
        self.log_mode: int = logging.INFO
        self.args: argparse.Namespace = argparse.Namespace()


def parse_arguments(options: Options) -> None:
    """Parse command-line arguments.

    Args:
        options: Options object to store parsed arguments. Contains:
            - my_name:           Name of the program.
            - default_dest_dir:  Default directory where files will be saved.
            - log_mode:          Logging mode (default is logging.INFO).
            - args:              Parsed arguments will be stored here.

    Returns:
        None, but updates options.args with parsed arguments.

    Raises:
        SystemExit: If the "-v"/"--version" flag is provided, the program
                    will print the relevant information and exit.
        ValueError: If any of the arguments are invalid.
    """
    parser = argparse.ArgumentParser(
        description=(
            f"Download a file using emmykit.download_file(). "
            f"{options.my_name} version {__version__}"
        )
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging."
    )
    parser.add_argument(
        "url",
        help="URL of the file to download. The filename is derived from the URL path.",
    )
    options.args = parser.parse_args()
    if options.args.debug:
        options.log_mode = logging.DEBUG


def determine_destination_path(url: str, dest_dir: str | os.PathLike[str]) -> Path:
    """Determine the destination path for a download based on the URL.

    Args:
        url:      URL that will be downloaded.
        dest_dir: Directory in which the file should be stored.

    Returns:
        Path representing the full destination path for the downloaded file.

    Raises:
        None
    """
    dest_dir_path: Path = Path(dest_dir)

    parsed = urlparse(url)
    url_path = Path(parsed.path) if parsed.path else Path()
    candidate = url_path.name

    if not candidate:
        # Fall back to host name, then to a generic name.
        import datetime as dt

        current_timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = parsed.netloc or f"download-{current_timestamp}"
        candidate = base_name.replace("/", "_")

    dest_path: Path = dest_dir_path / candidate

    return dest_path


def run_download(options: Options) -> None:
    """Perform the download based on parsed command-line options.

    Args:
        options: Options object containing:
            - my_name:           Name of the program.
            - default_dest_dir:  Default directory where files will be saved.
            - log_mode:          Logging mode in use.
            - args:              Parsed arguments from argparse. Must include:
                - url:   URL of the file to download.
                - debug: Whether debug logging is enabled.

    Returns:
        None

    Raises:
        SystemExit: Propagated if emmykit.download_file() exits on error.
    """
    url: str = options.args.url

    dest_path: Path = determine_destination_path(url, Path.cwd())

    logging.debug("Current working directory: %s", os.fspath(Path.cwd()))
    logging.info("Preparing to download URL: %s", url)
    logging.info("Destination file will be: %s", os.fspath(dest_path))

    if dest_path.exists():
        logging.warning(
            "Destination file already exists and will be overwritten: %s",
            os.fspath(dest_path),
        )

    # Delegate the actual download to the shared utility.
    ek.download_file(url=url, dest=dest_path, timeout=10000)

    logging.info("Download completed successfully: %s", os.fspath(dest_path))


def main() -> None:
    """Main function.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
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

    run_download(options)

    logging.shutdown()


if __name__ == "__main__":
    main()
