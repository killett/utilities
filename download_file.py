from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

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
    parsed = urlparse(url)
    # Take the name first, then decode: decoding first would let %2F inject a
    # separator and silently retarget the download.
    candidate = unquote(Path(parsed.path).name) if parsed.path else ""

    # "", "." and ".." are not usable filenames, and ".." would resolve
    # outside dest_dir. A decoded separator is equally unusable. All fall back
    # to the host, then to a generic timestamped name.
    if candidate in {"", ".", ".."} or "/" in candidate or "\\" in candidate:
        import datetime as dt

        current_timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        # hostname, not netloc: netloc carries userinfo and port, so a URL
        # with credentials would write them into the filename. hostname needs
        # the same guard as the path candidate: a URL like "https://../a/.."
        # has hostname "..", which would otherwise escape dest_dir unchecked.
        host = parsed.hostname or ""
        if host in {"", ".", ".."} or "/" in host or "\\" in host:
            host = ""
        candidate = host or f"download-{current_timestamp}"

    return Path(dest_dir) / candidate


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

    dest_path: Path = determine_destination_path(url, options.default_dest_dir)

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
