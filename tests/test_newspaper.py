"""Tests for newspaper helpers."""

from datetime import datetime

from podcast.newspaper import LAUNCH_DATE, _color_name_to_hex, _issue_number

# The full palette configured in config.yaml — every entry must resolve
PALETTE = [
    "burnt orange",
    "deep teal",
    "electric purple",
    "muted tan",
    "sage green",
    "dusty rose",
    "cobalt blue",
    "golden yellow",
    "terracotta red",
    "midnight navy",
    "moss green",
    "warm coral",
]


def test_every_palette_color_has_a_distinct_hex():
    hexes = [_color_name_to_hex(color) for color in PALETTE]
    assert all(h.startswith("#") for h in hexes)
    # Regression: 7 of 12 colors used to silently fall back to burnt orange
    fallback_count = sum(1 for h in hexes if h == "#ff6b35")
    assert fallback_count == 1  # only "burnt orange" itself


def test_hex_passthrough():
    assert _color_name_to_hex("#123abc") == "#123abc"


def test_unknown_color_falls_back():
    assert _color_name_to_hex("chartreuse dream") == "#ff6b35"


def test_issue_number_counts_from_launch():
    assert _issue_number(LAUNCH_DATE) == 1
    assert _issue_number(datetime(2025, 12, 15)) == 2
