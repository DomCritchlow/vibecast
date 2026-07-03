"""Tests for RSS feed generation from episode JSON."""

import json
from pathlib import Path

from podcast.rss_feed import create_feed_xml, episode_json_to_rss_metadata

CONFIG = {
    "podcast": {
        "title": "Test & Cast",
        "site_url": "https://example.com",
        "feed_url": "https://example.com/feed.xml",
        "description": "Desc",
        "author": "Author",
        "owner_email": "a@b.c",
        "artwork_url": "https://example.com/art.png",
    },
    "feed": {"max_episodes": 2},
}

EPISODES_DIR = Path(__file__).parent.parent / "podcast" / "episodes"


def _sample_episode():
    path = sorted(EPISODES_DIR.glob("*.json"))[-1]
    return json.loads(path.read_text())


def test_episode_json_converts_to_rss_metadata():
    metadata = episode_json_to_rss_metadata(_sample_episode(), CONFIG)
    assert metadata["guid"]
    assert metadata["url"].startswith("http")
    assert "IN THIS EPISODE" in metadata["description"]


def test_feed_xml_escapes_and_limits():
    episode = episode_json_to_rss_metadata(_sample_episode(), CONFIG)
    xml = create_feed_xml(CONFIG, [episode, episode, episode])
    assert "Test &amp; Cast" in xml
    # max_episodes=2 caps the item count
    assert xml.count("<item>") == 2
    assert '<guid isPermaLink="false">' in xml


def test_newspaper_url_lands_in_show_notes():
    episode = _sample_episode()
    episode["media"]["newspaper_url"] = "https://example.com/np.pdf"
    metadata = episode_json_to_rss_metadata(episode, CONFIG)
    assert "https://example.com/np.pdf" in metadata["description"]
