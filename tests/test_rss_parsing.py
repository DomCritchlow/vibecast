"""Tests for RSS HTML cleaning and date parsing."""

from datetime import datetime

from podcast.sources.rss import clean_html, parse_feed_date


def test_clean_html_strips_tags():
    assert clean_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_clean_html_decodes_named_entities():
    assert clean_html("Fish &amp; Chips &lt;3") == "Fish & Chips <3"


def test_clean_html_decodes_numeric_entities():
    # These were left raw by the old hand-rolled cleaner
    assert clean_html("It&#8217;s here&#8230;") == "It’s here…"


def test_clean_html_normalizes_whitespace():
    assert clean_html("  a\n\n  b\xa0c  ") == "a b c"


def test_parse_feed_date_rfc2822():
    parsed = parse_feed_date("Fri, 13 Dec 2025 08:00:00 +0000")
    assert parsed is not None
    assert (parsed.year, parsed.month, parsed.day) == (2025, 12, 13)


def test_parse_feed_date_iso():
    parsed = parse_feed_date("2026-07-01T12:30:00Z")
    assert parsed == datetime.fromisoformat("2026-07-01T12:30:00+00:00")


def test_parse_feed_date_garbage_returns_none():
    assert parse_feed_date("not a date") is None
    assert parse_feed_date("") is None
