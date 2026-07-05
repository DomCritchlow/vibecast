"""Tests for the fal.ai transport (no network calls)."""

import podcast.tts.fal_tts as fal_tts
from podcast.tts import get_tts_provider
from podcast.tts.fal_tts import FalTTSProvider, resolve_fal_voice

# --- voice resolution ---


def test_resolve_voice_from_id():
    # River's shared voice_id -> fal's voice-name form
    assert resolve_fal_voice("SAz9YHcvj6GT2YYXdXww") == "River"


def test_resolve_voice_from_preset_name():
    assert resolve_fal_voice("george") == "George"
    assert resolve_fal_voice("River") == "River"


def test_resolve_voice_passthrough_unknown():
    # An unknown value is assumed to already be a fal voice name
    assert resolve_fal_voice("SomeCustomVoice") == "SomeCustomVoice"


# --- provider config ---


def test_fal_provider_shares_elevenlabs_voice_id():
    config = {"tts": {"elevenlabs": {"voice_id": "SAz9YHcvj6GT2YYXdXww"}}}
    provider = FalTTSProvider(config)
    assert provider.voice == "River"
    assert provider.name == "fal.ai (ElevenLabs v3)"


def test_fal_provider_explicit_voice_overrides():
    config = {
        "tts": {
            "elevenlabs": {"voice_id": "SAz9YHcvj6GT2YYXdXww"},
            "fal": {"voice": "Brian"},
        }
    }
    assert FalTTSProvider(config).voice == "Brian"


def test_registry_builds_fal_by_name():
    config = {"tts": {"provider": "openai", "elevenlabs": {"voice_id": "river"}}}
    provider = get_tts_provider(config, provider_name="fal")
    assert isinstance(provider, FalTTSProvider)


# --- generation argument shaping (client stubbed) ---


def test_sound_effect_clamps_duration_and_sets_loop(monkeypatch):
    captured = {}

    def fake_generate(endpoint, arguments):
        captured["endpoint"] = endpoint
        captured["arguments"] = arguments
        return b"AUDIO"

    monkeypatch.setattr(fal_tts, "fal_generate_audio", fake_generate)

    out = fal_tts.fal_sound_effect("rain on glass", seconds=30, loop=True)
    assert out == b"AUDIO"
    assert captured["endpoint"] == fal_tts.SFX_ENDPOINT
    # fal caps a single SFX generation at 22s
    assert captured["arguments"]["duration_seconds"] == fal_tts.SFX_MAX_SECONDS
    assert captured["arguments"]["loop"] is True


def test_synthesize_shapes_tts_arguments(monkeypatch):
    calls = []

    def fake_generate(endpoint, arguments):
        calls.append((endpoint, arguments))
        return b"CHUNK"

    monkeypatch.setattr(fal_tts, "fal_generate_audio", fake_generate)
    monkeypatch.setenv("FAL_KEY", "test-key")

    config = {"tts": {"elevenlabs": {"voice_id": "river"}, "fal": {"speed": 1.0}}}
    provider = FalTTSProvider(config)
    provider._available = True

    audio = provider.synthesize("Hello there.")
    assert audio == b"CHUNK"
    endpoint, args = calls[0]
    assert endpoint == fal_tts.TTS_ENDPOINT
    assert args["voice"] == "River"
    assert args["text"] == "Hello there."
    # speed == 1.0 is the default and should be omitted
    assert "speed" not in args
