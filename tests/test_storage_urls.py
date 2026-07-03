"""Tests for R2 URL construction (no network)."""

from podcast.storage import get_fallback_artwork_url, public_url_for_key

CONFIG = {
    "storage": {"r2": {"bucket": "vibecast", "public_base_url": "https://pub-x.r2.dev/"}},
    "artwork": {"r2_fallback_key": "static/default-episode-art.png"},
}


def test_public_url_uses_object_key():
    # Regression: mp3 URLs used to hardcode /episodes/ regardless of key_prefix
    assert (
        public_url_for_key("shows/2026-07-03.mp3", CONFIG)
        == "https://pub-x.r2.dev/shows/2026-07-03.mp3"
    )


def test_fallback_artwork_url():
    assert get_fallback_artwork_url(CONFIG) == "https://pub-x.r2.dev/static/default-episode-art.png"
