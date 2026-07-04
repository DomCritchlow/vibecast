"""Tests for Telegram notification composition (no API calls)."""

import pytest

from podcast.notify import (
    CAPTION_LIMIT,
    NotifyError,
    already_notified,
    build_caption,
    build_reply_markup,
    episode_too_old,
    fallback_note,
    resolve_listen_url,
)

CONFIG = {
    "vibe": {"voice_persona": {"name": "Testo"}},
    "podcast": {
        "site_url": "https://example.github.io/vibecast/",
        "artwork_url": "https://example.github.io/vibecast/artwork.png",
    },
    "notifications": {"telegram": {"enabled": True}},
}

EPISODE = {
    "guid": "2026-07-04",
    "date": "2026-07-04T05:00:00",
    "title": "Fusion Milestone & Ocean Mapping <Update>",
    "duration_formatted": "4:25",
    "media": {
        "audio_url": "https://cdn.example.com/episodes/2026-07-04.mp3",
        "artwork_url": "https://cdn.example.com/episodes/2026-07-04/episode-art.png",
        "newspaper_url": "https://cdn.example.com/episodes/2026-07-04/newspaper.pdf",
        "transcript_url": "https://cdn.example.com/transcripts/2026-07-04.txt",
    },
    "stories": [
        {"title": "Story One.", "source": "Src", "url": "https://x.com/1", "summary": "Sum"},
        {"title": "Story Two", "source": "Src", "url": "https://x.com/2", "summary": "Sum"},
    ],
}


# ---------------------------------------------------------------------------
# Listen URL resolution
# ---------------------------------------------------------------------------


def test_listen_url_defaults_to_site_listen_page():
    assert resolve_listen_url(CONFIG) == "https://example.github.io/vibecast/listen.html"


def test_listen_url_prefers_apple_podcast_id():
    config = {
        **CONFIG,
        "notifications": {"telegram": {"apple_podcast_id": "1234567890"}},
    }
    assert resolve_listen_url(config) == "https://overcast.fm/itunes1234567890"


def test_listen_url_explicit_override_wins():
    config = {
        **CONFIG,
        "notifications": {
            "telegram": {
                "listen_url": "https://overcast.fm/+custom",
                "apple_podcast_id": "1234567890",
            }
        },
    }
    assert resolve_listen_url(config) == "https://overcast.fm/+custom"


def test_listen_url_fails_without_site_url():
    with pytest.raises(NotifyError):
        resolve_listen_url({"podcast": {}, "notifications": {}})


# ---------------------------------------------------------------------------
# Caption + note
# ---------------------------------------------------------------------------


def test_fallback_note_mentions_persona_and_lead_story():
    note = fallback_note(EPISODE, CONFIG)
    assert "Testo" in note
    assert "Story One" in note
    assert "4:25" in note


def test_caption_escapes_html_and_includes_meta():
    caption = build_caption(EPISODE, "A note about <things> & stuff")
    assert "<b>Fusion Milestone &amp; Ocean Mapping &lt;Update&gt;</b>" in caption
    assert "&lt;things&gt; &amp; stuff" in caption
    assert "4:25" in caption
    assert "2 stories" in caption


def test_caption_clamps_to_telegram_limit():
    caption = build_caption(EPISODE, "word " * 400)
    assert len(caption) <= CAPTION_LIMIT
    assert caption.startswith("<b>")  # title survives the trim
    assert caption.rstrip().endswith("</i>")  # meta line survives the trim


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------


def test_keyboard_has_listen_button_plus_extras():
    markup = build_reply_markup(EPISODE, CONFIG)
    rows = markup["inline_keyboard"]
    assert rows[0][0]["text"] == "🎧 Listen in Overcast"
    assert rows[0][0]["url"] == "https://example.github.io/vibecast/listen.html"
    second_row_urls = [b["url"] for b in rows[1]]
    assert EPISODE["media"]["newspaper_url"] in second_row_urls
    assert EPISODE["media"]["transcript_url"] in second_row_urls


def test_keyboard_omits_missing_or_disabled_extras():
    config = {
        **CONFIG,
        "notifications": {"telegram": {"buttons": {"newspaper": False, "transcript": True}}},
    }
    episode = {**EPISODE, "media": {**EPISODE["media"], "transcript_url": None}}
    markup = build_reply_markup(episode, config)
    assert len(markup["inline_keyboard"]) == 1  # only the listen button row


# ---------------------------------------------------------------------------
# Idempotence + staleness guards
# ---------------------------------------------------------------------------


def test_already_notified_reads_marker():
    assert not already_notified(EPISODE)
    stamped = {**EPISODE, "notifications": {"telegram": {"sent_at": "2026-07-04T10:00:00"}}}
    assert already_notified(stamped)


def test_episode_too_old_guards_stale_episodes():
    assert episode_too_old({"date": "2020-01-01T05:00:00"}, max_age_hours=36)
    assert episode_too_old({}, max_age_hours=36)  # unparseable = don't send
