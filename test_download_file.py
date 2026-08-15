"""Tests for download_file.py."""

from __future__ import annotations

import re
from pathlib import Path

import download_file

DEST = Path("/tmp/dl")


def test_filename_comes_from_the_url_path() -> None:
    # Catches using the host unconditionally, so every download would land
    # under the host name instead of the file's own.
    assert (
        download_file.determine_destination_path(
            "https://example.com/dir/file.bin", DEST
        )
        == DEST / "file.bin"
    )


def test_query_and_fragment_are_not_part_of_the_filename() -> None:
    # RFC 3986: query and fragment are not part of the path. Catches matching
    # on the raw URL, which yields an illegal filename.
    assert (
        download_file.determine_destination_path(
            "https://example.com/file.bin?v=2#frag", DEST
        )
        == DEST / "file.bin"
    )


def test_percent_encoding_is_decoded() -> None:
    # RFC 3986: %20 is a space. download_torrents.safe_filename_from_url()
    # already unquotes; this file did not, so the file landed on disk named
    # "my%20file.bin".
    assert (
        download_file.determine_destination_path(
            "https://example.com/my%20file.bin", DEST
        )
        == DEST / "my file.bin"
    )


def test_dot_dot_path_cannot_escape_the_destination_directory() -> None:
    # Previously returned DEST/"..", the PARENT of the download directory --
    # the URL decided where the write landed.
    assert (
        download_file.determine_destination_path("https://example.com/a/b/../..", DEST)
        == DEST / "example.com"
    )


def test_encoded_dot_dot_cannot_escape_either() -> None:
    # This test keeps the two halves of the fix paired. Adding unquote() on
    # its own turns %2E%2E into a working "..", introducing a traversal that
    # does not exist today.
    assert (
        download_file.determine_destination_path("https://example.com/%2E%2E", DEST)
        == DEST / "example.com"
    )


def test_encoded_separator_does_not_retarget_the_download() -> None:
    # Decoding before splitting would silently yield "b.bin" -- a different
    # file from the one the URL named.
    assert (
        download_file.determine_destination_path("https://example.com/a%2Fb.bin", DEST)
        == DEST / "example.com"
    )


def test_credentials_and_port_are_not_written_into_the_filename() -> None:
    # netloc is "user:pass@example.com:8080" -- using it writes credentials to
    # disk in a filename. hostname is "example.com" per RFC 3986's authority
    # grammar.
    assert (
        download_file.determine_destination_path(
            "https://user:pass@example.com:8080", DEST
        )
        == DEST / "example.com"
    )


def test_url_with_neither_path_nor_host_falls_back_to_a_timestamp() -> None:
    # Catches a broken fallback chain producing an empty filename. Asserted by
    # regex against the %Y%m%d_%H%M%S format string, so no clock is frozen and
    # no dependency is added.
    result = download_file.determine_destination_path("", DEST)

    assert result.parent == DEST
    assert re.fullmatch(r"download-\d{8}_\d{6}", result.name), result.name


def test_hostile_host_falls_back_to_a_timestamp_instead_of_escaping() -> None:
    # hostname for "https://../a/.." is itself "..", so an unguarded fallback
    # returns dest_dir/.., the parent of the download directory -- the same
    # escape the path-candidate guard exists to close, reachable through the
    # host instead of the path.
    result = download_file.determine_destination_path("https://../a/..", DEST)

    assert result.parent == DEST
    assert re.fullmatch(r"download-\d{8}_\d{6}", result.name), result.name


def test_destination_directory_argument_is_respected(tmp_path: Path) -> None:
    # Catches hardcoding Path.cwd() and ignoring the argument.
    a = download_file.determine_destination_path(
        "https://example.com/f.bin", tmp_path / "a"
    )
    b = download_file.determine_destination_path(
        "https://example.com/f.bin", tmp_path / "b"
    )

    assert (a.parent.name, b.parent.name) == ("a", "b")
    assert a.name == b.name == "f.bin"
