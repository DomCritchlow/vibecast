"""Tests for episode schema and config validation."""

import json
from pathlib import Path

import pytest

from podcast.models import ConfigError, Episode, validate_config

EPISODES_DIR = Path(__file__).parent.parent / "podcast" / "episodes"


def test_all_existing_episodes_validate():
    episode_files = sorted(EPISODES_DIR.glob("*.json"))
    assert episode_files, "expected existing episode JSON files"
    for path in episode_files:
        Episode.model_validate(json.loads(path.read_text()))


def test_episode_rejects_bad_guid():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Episode.model_validate(
            {
                "guid": "not-a-date",
                "date": "2026-07-03T00:00:00",
                "title": "t",
                "media": {"audio_url": "https://x/e.mp3"},
                "metadata": {"created_at": "2026-07-03T00:00:00"},
            }
        )


def test_validate_config_accepts_minimal():
    config = {
        "podcast": {"title": "T", "site_url": "https://x", "feed_url": "https://x/feed.xml"},
        "storage": {"r2": {"bucket": "b"}},
        "sources": {"rss": [{"name": "s", "url": "https://x/rss", "enabled": True}]},
        "tts": {"provider": "openai"},
    }
    assert validate_config(config) is config


def test_validate_config_reports_all_problems():
    with pytest.raises(ConfigError) as exc:
        validate_config({"tts": {"provider": "nope"}})
    message = str(exc.value)
    assert "podcast.title" in message
    assert "storage.r2.bucket" in message
    assert "tts.provider" in message


def test_validate_config_allows_missing_urls():
    # site_url/feed_url come from env secrets; missing ones only warn
    config = {
        "podcast": {"title": "T"},
        "storage": {"r2": {"bucket": "b"}},
        "sources": {"rss": [{"name": "s", "url": "https://x/rss", "enabled": True}]},
        "tts": {"provider": "openai"},
    }
    assert validate_config(config) is config
