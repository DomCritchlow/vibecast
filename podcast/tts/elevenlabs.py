"""ElevenLabs TTS provider.

Voices the produced ("special") episodes — see podcast/production.py — and
can also be used as the everyday provider via tts.provider: "elevenlabs".

Notes on the current API (July 2026):
- eleven_v3 is GA: the most expressive model, accepts up to 5,000 chars per
  request and honors inline audio tags like [chuckles] or [whispers].
- v3 handles voice settings differently from v2 (stability is banded, not
  continuous), so we let the API defaults drive v3 and only send the
  stability/similarity knobs to v2-family models.
- Output is used exactly as returned — no post-processing (the enhancement
  presets in audio_processing.py exist to clean up OpenAI TTS artifacts).

Setup:
1. Set ELEVENLABS_API_KEY (GitHub secret for CI, .env locally)
2. Pick a voice: uv run python scripts/audition_voices.py
3. Configure tts.elevenlabs (and tts.special_episodes) in config.yaml

API pricing (pay-as-you-go, July 2026): ~$0.10/1k chars on v3, so a typical
episode runs ~$0.60 plus pennies for sound effects.
"""

import logging
import os

from .base import TTSProvider

logger = logging.getLogger(__name__)


class ElevenLabsTTSProvider(TTSProvider):
    """Text-to-speech using the ElevenLabs API.

    Configuration in config.yaml:
        tts:
          elevenlabs:
            voice_id: "george"          # preset name or a raw voice ID
            model_id: "eleven_v3"
            format: "mp3_44100_128"
            # v2-family models only:
            stability: 0.5
            similarity_boost: 0.75
    """

    # Well-known default-library voices, by name. Any other value in
    # config is treated as a raw voice ID (browse elevenlabs.io/voice-library
    # or run scripts/audition_voices.py to hear current options).
    PRESET_VOICES = {
        # Current default library
        "george": "JBFqnCBsd6RMkjVDRZzb",  # British, warm narrator
        "daniel": "onwK4e9ZLuTAKqWW03F9",  # British, authoritative
        "brian": "nPczCjzI2devNBz1zQrb",  # American, deep narrator
        "will": "bIHbv24MWmeRgasZH58o",  # American, friendly
        "eric": "cjVigY5qzO86Huf0OWal",  # American, friendly
        "chris": "iP95p4xoKVk53GoZ742B",  # American, casual
        "liam": "TX3LPaxmHKxFdv7VOQHJ",  # American, articulate
        "callum": "N2lVS1w4EtoT3dr4eOWO",  # Transatlantic, intense
        "lily": "pFZP5JQG7iQjIQuC4Bku",  # British, warm
        "jessica": "cgSgspJ2msm6clMCkdW9",  # American, expressive
        "laura": "FGY2WhTYpPnrIDTdsKH5",  # American, upbeat
        "sarah": "EXAVITQu4vr4xnSDxMaL",  # American, soft news
        "charlotte": "XB0fDUnXU5powFXDhCwa",  # Swedish accent, seductive
        "alice": "Xb7hH8MSUJpSbSDYk0k2",  # British, confident
        "matilda": "XrExE9yKIg1WjnnlVkGX",  # American, friendly
        "river": "SAz9YHcvj6GT2YYXdXww",  # American, neutral
        # Legacy voices kept for backward compatibility
        "rachel": "21m00Tcm4TlvDq8ikWAM",
        "adam": "pNInz6obpgDQGcFmaJgB",
        "josh": "TxGEqnHWrfWFTfGW9XjX",
        "drew": "29vD33N1CtxCmqQRPOHJ",
    }

    MODELS = {
        "eleven_v3": "Most expressive — supports inline audio tags like [excited]",
        "eleven_multilingual_v2": "High quality, stable, multilingual",
        "eleven_flash_v2_5": "Lowest latency, half the cost per character",
    }

    # Character limit per request, by model family
    MAX_CHARS_V3 = 5000
    MAX_CHARS_V2 = 10000
    MAX_CHARS_FLASH = 40000

    def __init__(self, config: dict):
        super().__init__(config)

        # Check if elevenlabs is installed
        self._client = None
        self._available = self._check_availability()

        if not self._available:
            return

        self.elevenlabs_config = self.tts_config.get("elevenlabs", {})

        # Get settings
        self.voice_id = self._resolve_voice_id(self.elevenlabs_config.get("voice_id", "george"))
        self.model_id = self.elevenlabs_config.get("model_id", "eleven_v3")
        self.stability = self.elevenlabs_config.get("stability", 0.5)
        self.similarity_boost = self.elevenlabs_config.get("similarity_boost", 0.75)
        # 192k output is gated to the Creator subscription tier; 128k is the
        # ceiling on pay-as-you-go API plans.
        self.output_format = self.elevenlabs_config.get("format", "mp3_44100_128")

    def _check_availability(self) -> bool:
        """Check if ElevenLabs is properly configured."""
        # Check for API key
        if not os.environ.get("ELEVENLABS_API_KEY"):
            return False

        # Check if library is installed
        try:
            from elevenlabs import ElevenLabs

            self._client = ElevenLabs()
            return True
        except ImportError:
            return False
        except Exception as e:
            logger.warning(f"ElevenLabs init failed: {e}")
            return False

    def _resolve_voice_id(self, voice: str) -> str:
        """Resolve voice name to ID if using a preset."""
        if voice.lower() in self.PRESET_VOICES:
            return self.PRESET_VOICES[voice.lower()]
        return voice

    @property
    def name(self) -> str:
        return "ElevenLabs TTS"

    @property
    def max_chars(self) -> int:
        model_id = getattr(self, "model_id", "")
        if model_id.startswith("eleven_v3"):
            return self.MAX_CHARS_V3
        if model_id.startswith("eleven_flash"):
            return self.MAX_CHARS_FLASH
        return self.MAX_CHARS_V2

    @property
    def supported_formats(self) -> list[str]:
        return ["mp3_44100_128", "mp3_44100_192", "pcm_16000", "pcm_22050", "pcm_24000"]

    def _voice_settings(self):
        """Voice settings for v2-family models; v3 runs on API defaults."""
        if self.model_id.startswith("eleven_v3"):
            return None

        from elevenlabs import VoiceSettings

        return VoiceSettings(
            stability=self.stability,
            similarity_boost=self.similarity_boost,
        )

    def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio using ElevenLabs.

        Raises:
            RuntimeError: If ElevenLabs is not available.
        """
        if not self._available:
            raise RuntimeError(
                "ElevenLabs is not available. Make sure you have:\n"
                "1. Installed: uv sync (elevenlabs is a project dependency)\n"
                "2. Set ELEVENLABS_API_KEY environment variable\n"
                "3. Configured tts.elevenlabs in config.yaml"
            )

        chunks = self.chunk_text(text)

        if len(chunks) > 1:
            logger.info(f"  Text is {len(text)} chars, splitting into {len(chunks)} chunks")

        audio_parts = []
        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                logger.info(f"  Synthesizing chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...")

            response = self._client.text_to_speech.convert(
                voice_id=self.voice_id,
                model_id=self.model_id,
                text=chunk,
                output_format=self.output_format,
                voice_settings=self._voice_settings(),
            )

            # Response is a generator of bytes
            audio_bytes = b"".join(response)
            audio_parts.append(audio_bytes)

        return b"".join(audio_parts)


def get_voice_description(voice: str) -> str | None:
    """Get a description for an ElevenLabs preset voice."""
    descriptions = {
        "george": "British male - warm storyteller, natural narrator",
        "daniel": "British male - clear and authoritative",
        "brian": "American male - deep, easygoing narrator",
        "will": "American male - friendly and conversational",
        "callum": "Transatlantic male - textured and intense",
        "lily": "British female - warm and engaging",
        "jessica": "American female - bright and expressive",
        "sarah": "American female - soft, news-style delivery",
        "alice": "British female - confident and clear",
    }
    return descriptions.get(voice.lower())
