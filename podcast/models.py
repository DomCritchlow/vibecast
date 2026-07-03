"""Typed models for episode metadata and config validation.

Episode JSON files in podcast/episodes/ are the single source of truth for
the feed and the website, so writes go through the Episode model to catch
malformed data before it lands on disk.
"""

import logging

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class Story(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    source: str
    url: str
    summary: str = ""


class ReadingRef(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    author: str = ""
    source: str = ""
    url: str
    description: str = ""


class EpisodeMedia(BaseModel):
    model_config = ConfigDict(extra="allow")

    audio_url: str
    audio_size_bytes: int = 0
    artwork_url: str | None = None
    newspaper_url: str | None = None
    transcript_url: str | None = None


class EpisodeMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    # Optional because episodes migrated from R2 carry migrated_at instead
    created_at: str = ""
    llm_provider: str = "openai"
    llm_model: str = ""
    tts_provider: str = ""
    tts_voice: str = ""


class Episode(BaseModel):
    model_config = ConfigDict(extra="allow")

    guid: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    date: str
    title: str
    tagline: str = ""
    duration_seconds: float = 0.0
    duration_formatted: str = ""
    media: EpisodeMedia
    stories: list[Story] = Field(default_factory=list)
    reading_list: list[ReadingRef] = Field(default_factory=list)
    metadata: EpisodeMetadata


class ConfigError(ValueError):
    """Raised when config.yaml is missing required settings."""


def validate_config(config: dict) -> dict:
    """Sanity-check the loaded config and return it.

    The config is intentionally kept as a plain dict (it is large and mostly
    free-form vibe text), but the settings the pipeline can't run without are
    checked up front so a bad config fails loudly at step 1 instead of
    halfway through an episode.
    """
    problems = []

    podcast = config.get("podcast") or {}
    if not podcast.get("title"):
        problems.append("podcast.title is required")

    # These normally arrive via VIBECAST_* env vars / GitHub secrets; missing
    # values produce an invalid feed but shouldn't block local testing.
    for key in ("site_url", "feed_url"):
        if not podcast.get(key):
            logger.warning(
                "podcast.%s is not set (set VIBECAST_%s) — feed will not validate",
                key,
                key.upper(),
            )

    storage = (config.get("storage") or {}).get("r2") or {}
    if not storage.get("bucket"):
        problems.append("storage.r2.bucket is required")

    sources = config.get("sources") or {}
    rss = sources.get("rss") or []
    if not any(s.get("enabled", True) for s in rss):
        problems.append("at least one enabled sources.rss entry is required")

    tts = config.get("tts") or {}
    if tts.get("provider") not in ("openai", "elevenlabs"):
        problems.append("tts.provider must be 'openai' or 'elevenlabs'")

    if problems:
        raise ConfigError("Invalid config.yaml: " + "; ".join(problems))

    return config
