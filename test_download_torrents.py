"""Tests for download_torrents.py."""

from __future__ import annotations

import download_torrents

BASE = "https://example.com/list/page.html"


def test_links_are_resolved_against_the_base_url() -> None:
    html = """
    <a href="a.torrent">relative</a>
    <a href="/dl/b.torrent">root-relative</a>
    <a href="https://cdn.example.org/c.torrent">absolute</a>
    <a href="notes.txt">not a torrent</a>
    <a>no href at all</a>
    """

    assert download_torrents.extract_torrent_links(html, BASE) == {
        "https://example.com/list/a.torrent",
        "https://example.com/dl/b.torrent",
        "https://cdn.example.org/c.torrent",
    }


def test_surrounding_whitespace_is_stripped_before_joining() -> None:
    # urljoin() drops a leading space but keeps a trailing one, and a URL
    # ending in "torrent " is not recognised as a .torrent link, so the link
    # would be silently dropped without the strip().
    html = '<a href=" /dl/b.torrent ">padded</a>'

    assert download_torrents.extract_torrent_links(html, BASE) == {
        "https://example.com/dl/b.torrent"
    }


def test_two_spellings_of_the_same_target_collapse_to_one() -> None:
    html = '<a href="a.torrent">one</a><a href="./a.torrent">two</a>'

    assert download_torrents.extract_torrent_links(html, BASE) == {
        "https://example.com/list/a.torrent"
    }


def test_query_string_and_fragment_do_not_hide_the_extension() -> None:
    html = '<a href="d.torrent?id=1#frag">tracked</a>'

    assert download_torrents.extract_torrent_links(html, BASE) == {
        "https://example.com/list/d.torrent?id=1#frag"
    }


def test_is_torrent_url_unquotes_the_path() -> None:
    assert download_torrents.is_torrent_url("https://example.com/e%2Etorrent") is True


def test_is_torrent_url_rejects_other_extensions() -> None:
    assert download_torrents.is_torrent_url("https://example.com/e.txt") is False
    assert download_torrents.is_torrent_url("https://example.com/torrent") is False
