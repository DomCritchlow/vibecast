"""Tests for prompt building and script cleaning (no API calls)."""

from podcast.sources.base import ContentItem
from podcast.sources.reading_list import ReadingListItem
from podcast.writer import (
    _writer_config,
    build_system_prompt,
    build_user_prompt,
    clean_script_for_tts,
    generate_script_dry_run,
)

CONFIG = {
    "vibe": {
        "name": "Test Vibe",
        "voice_persona": {"name": "Testo", "greetings": ["Hi."], "closings": ["Bye."]},
    },
    "podcast": {"title": "Testcast"},
    "episode": {"target_minutes": 4},
    "writer": {
        "provider": "anthropic",
        "anthropic": {"model": "claude-opus-4-8"},
        "openai": {"model": "gpt-5.4-mini"},
    },
}

ITEMS = [ContentItem(title="Story One", url="https://x.com/1", source="Src", summary="Sum")]
READING = [
    ReadingListItem(
        title="Long Read",
        url="https://x.com/read",
        source="Blog",
        summary="An essay about things",
        author="Jane",
    )
]


def test_clean_script_removes_stage_directions():
    script = "[intro music]\nHello there.\n[pause]\nGoodbye.\n[fade out]"
    cleaned = clean_script_for_tts(script)
    assert "music" not in cleaned
    assert "fade" not in cleaned
    assert "..." in cleaned  # [pause] becomes ellipsis
    assert "Hello there." in cleaned


def test_system_prompt_includes_persona():
    prompt = build_system_prompt(CONFIG)
    assert "You are Testo" in prompt
    assert "Testcast" in prompt


def test_user_prompt_includes_stories_and_reading_list():
    prompt = build_user_prompt("Sunny.", ITEMS, CONFIG, READING)
    assert "Story One" in prompt
    assert "Sunny." in prompt
    # Regression: the reading list used to be built but never interpolated
    assert "Long Read" in prompt
    assert "by Jane" in prompt


def test_dry_run_reports_configured_model():
    result = generate_script_dry_run("Sunny.", ITEMS, CONFIG)
    assert "claude-opus-4-8" in result["model"]
    assert result["provider"] == "anthropic"
    assert "DRY RUN" in result["script"]


def test_writer_config_falls_back_to_legacy_openai_llm():
    legacy = {"openai": {"llm": {"model": "gpt-4.1-mini"}}}
    cfg = _writer_config(legacy)
    assert cfg["provider"] == "openai"
    assert cfg["openai"]["model"] == "gpt-4.1-mini"


def test_score_episode_quality_parses_and_clamps(monkeypatch):
    import podcast.writer as writer

    class FakeWriter:
        provider_name = "fake"
        model = "fake"

        def generate_json(self, system, user, schema, max_tokens=2000):
            return {"score": 1.4, "reason": "huge day"}  # out of range on purpose

    monkeypatch.setattr(writer, "get_writer", lambda config: FakeWriter())
    # Score is clamped into [0, 1]
    assert writer.score_episode_quality(ITEMS, CONFIG) == 1.0


def test_score_episode_quality_safe_on_failure(monkeypatch):
    import podcast.writer as writer

    class BoomWriter:
        def generate_json(self, *a, **k):
            raise RuntimeError("api down")

    monkeypatch.setattr(writer, "get_writer", lambda config: BoomWriter())
    # A broken scoring call must never accidentally trigger a special
    assert writer.score_episode_quality(ITEMS, CONFIG) == 0.0
