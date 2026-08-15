#!/usr/bin/env python3
"""Download all .torrent files linked from a given web page.

Usage:
  python scrape_torrents.py https://example.com/page-with-links
  python scrape_torrents.py -debug -out ./torrents https://example.com
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

__version__: str = "1.1.1"


class Options:
    """Class that has all global options in one place."""

    def __init__(self) -> None:
        """Initialize the Options class with default values."""
        # The invoked name of this script, without the .py extension.
        self.my_name: str = Path(sys.argv[0]).stem
        # Use the --debug command line argument to change to DEBUG.
        self.log_mode: int = logging.INFO
        self.args: argparse.Namespace = argparse.Namespace()
        # self.default_out_dir = Path("~").expanduser() / "Desktop" / "ADD_TORRENTS_HERE_TO_DOWNLOAD"
        self.default_out_dir: Path = (
            Path("~").expanduser() / "Desktop" / "torrents_temp"
        )
        # Default keyword to search for in links, if any.
        self.default_keyword: str | None = None


def parse_arguments(options: Options) -> None:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=f"Read a web page and download all linked .torrent files.  {options.my_name} version {__version__}"
    )
    parser.add_argument(
        "url",
        type=str,
        metavar="URL_OR_FILE",
        help="Web page URL (http/https) or path to a local HTML file (or file:// URI).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=options.default_out_dir,
        help=f"Output directory (default: {options.default_out_dir}).",
    )
    parser.add_argument(
        "--keyword",
        default=options.default_keyword,
        help=f"Keyword to search for in links (default: {options.default_keyword}).",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging."
    )
    options.args = parser.parse_args()

    if options.args.debug:
        options.log_mode = logging.DEBUG
    # If no arguments are provided, print a short guide
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)


def looks_like_http_url(s: str) -> bool:
    """Check if a string looks like an HTTP or HTTPS URL.

    This is a basic check, not a full URL validation.
    """
    return s.casefold().startswith(("http://", "https://"))


def read_html_from_source(source: str, timeout: int = 20) -> tuple[str, str]:
    """Return (html, base_url) for a local file, a file:// URL or an HTTP(S) URL.

    A local file path or file:// URL is read from disk and gets a file:// base;
    anything else is fetched over HTTP(S).
    """
    parsed = urlparse(source)

    # file:// URI
    if parsed.scheme == "file":
        path = Path(unquote(parsed.path)).expanduser().resolve()
        html = path.read_text(encoding="utf-8", errors="ignore")
        return html, path.as_uri()

    # plain path (no scheme) -> treat as local file
    if not parsed.scheme and Path(source).expanduser().exists():
        path = Path(source).expanduser().resolve()
        html = path.read_text(encoding="utf-8", errors="ignore")
        return html, path.as_uri()

    # otherwise, assume HTTP(S)
    if looks_like_http_url(source):
        html = get_page_html(source, timeout=timeout)
        return html, source

    # fallback: if it doesn't look like http(s) and file doesn't exist, raise
    raise OSError(f"Not a file and not an http(s) URL: {source}")


def get_page_html(url: str, timeout: int = 20) -> str:
    """Fetch a web page and return its HTML content as a string."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    logging.debug("Fetching page: %s", url)
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    logging.debug("Fetched %d bytes of HTML", len(resp.text))
    return resp.text


def is_torrent_url(href: str) -> bool:
    """Decide whether a link points to a .torrent file.

    Checks the URL path (ignoring querystring and fragment).
    """
    parsed = urlparse(href)
    path = parsed.path or ""
    # unquote to catch encoded extensions like ".torrent%20"
    path_unquoted = unquote(path)
    return path_unquoted.lower().endswith(".torrent")


def extract_torrent_links(html: str, base_url: str) -> set[str]:
    """Parse HTML and extract all unique .torrent links as absolute URLs."""
    soup = BeautifulSoup(html, "html.parser")
    links: set[str] = set()
    for a in soup.find_all("a", href=True):
        raw_href = a["href"]
        if not isinstance(raw_href, str):
            # BeautifulSoup returns a list for multi-valued attributes such as
            # class. href is single-valued for every parser we use, so this
            # only guards against markup no parser we have produces.
            logging.debug("Skipping <a> with non-string href: %r", raw_href)
            continue
        href = raw_href.strip()
        absolute = urljoin(base_url, href)
        if is_torrent_url(absolute):
            links.add(absolute)
    logging.debug("Found %d unique .torrent links", len(links))
    return links


def safe_filename_from_url(file_url: str) -> str:
    """Derive a safe local filename from a URL."""
    parsed = urlparse(file_url)
    name = unquote(Path(parsed.path).name)
    # Basic safety: strip weird chars
    name = re.sub(r"[^\w\-. ]", "_", name)
    if not name.lower().endswith(".torrent"):
        name += ".torrent"
    return name


def download_file(
    url: str, dest_dir: str | os.PathLike[str], timeout: int = 60
) -> Path:
    """Stream a single file to disk, skipping it if it already has nonzero size.

    Returns the destination path.
    """
    dest_dir = Path(dest_dir).expanduser().resolve()
    if dest_dir.is_file():
        raise ValueError(f"Destination {dest_dir} is a file, not a directory.")
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = safe_filename_from_url(url)
    dest = dest_dir / fname

    if dest.exists() and dest.stat().st_size > 0:
        logging.info(f"Already exists, skipping: {dest}")
        return dest

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    logging.info("Downloading: %s", url)
    with requests.get(url, headers=headers, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        # Try to get size for nicer logs (optional)
        total = int(r.headers.get("Content-Length", "0")) or None
        written = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                f.write(chunk)
                written += len(chunk)
                if total:
                    pct = (written / total) * 100
                    logging.debug("... %s: %.1f%%", fname, pct)
    logging.info("Saved to: %s", dest)
    return dest


def download_all(links: Iterable[str], out_dir: Path, keyword: str | None) -> None:
    """Download all files from the given set of links to the specified directory.

    Logs errors but continues downloading others.
    """
    count = 0
    # for link in sorted(links, reverse=True):  # Download S21 before S20 because I'm downloading links from the same page after it's been updated with newer (later season) links.
    for link in links:
        try:
            if keyword is None or keyword.strip().casefold() in link.casefold():
                download_file(link, out_dir)
                count += 1
        except requests.HTTPError as e:
            logging.error("HTTP error for %s: %s", link, e)
        except requests.RequestException as e:
            logging.error("Request failed for %s: %s", link, e)
        except OSError as e:
            logging.error("File error for %s: %s", link, e)
    if count == 0:
        logging.warning("No files downloaded.")
    else:
        logging.info("Finished: %d file(s) downloaded.", count)


def main() -> None:
    """Main function."""
    options: Options = Options()
    parse_arguments(options)
    logging.basicConfig(
        level=options.log_mode,
        format="%(levelname)s - %(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    url = options.args.url
    out_dir = Path(options.args.out)
    keyword = options.args.keyword

    # Note for users: writing to /torrents may require elevated permissions.
    if str(out_dir).startswith(os.sep) and not os.access(
        out_dir.parent or Path("/"), os.W_OK
    ):
        logging.warning(
            "You may need elevated permissions to write to %s. "
            "Consider using a user-writable path with -out ./torrents",
            out_dir,
        )

    try:
        html, base_url = read_html_from_source(url)
    except (requests.RequestException, OSError) as e:
        logging.error("Failed to load source: %s", e)
        sys.exit(2)

    links = extract_torrent_links(html, base_url)
    if not links:
        logging.warning("No .torrent links found on the page.")
        logging.warning(f"Here is the html content:\n{html[:10000]}")
        with open("debug_fetched.html", "w", encoding="utf-8") as f:
            f.write(html)
        return

    download_all(links, out_dir, keyword)


if __name__ == "__main__":
    main()
