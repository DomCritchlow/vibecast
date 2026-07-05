"""fal.ai transport for the ElevenLabs models (TTS, sound effects, music).

Same ElevenLabs models we use directly — Eleven v3 (with audio tags),
Sound Effects V2 (with seamless loop), and Music — but served pay-per-use
through fal.ai: no subscription, commercial use allowed. This is the
no-subscription path; the native ElevenLabs provider is kept intact so we
can switch back by setting a provider to "elevenlabs".

Selected by setting a provider to "fal" (tts.provider for the daily driver,
or tts.special_episodes.provider for produced episodes).

fal returns a URL to the generated audio; we download it and return bytes so
the rest of the pipeline never has to know which transport produced it.
"""

import logging
import os

import httpx

from .base import TTSProvider
from .elevenlabs import ElevenLabsTTSProvider

logger = logging.getLogger(__name__)

TTS_ENDPOINT = "fal-ai/elevenlabs/tts/eleven-v3"
SFX_ENDPOINT = "fal-ai/elevenlabs/sound-effects/v2"
MUSIC_ENDPOINT = "fal-ai/elevenlabs/music"

# fal's sound-effects endpoint caps a single generation at 22 seconds.
SFX_MAX_SECONDS = 22.0

# fal identifies the built-in voices by NAME, not by voice_id, so we invert
# the shared roster to translate our config's voice_id into fal's form.
_ID_TO_NAME = {vid: name for name, vid in ElevenLabsTTSProvider.PRESET_VOICES.items()}


def fal_available() -> bool:
    """True if a fal API key is configured."""
    return bool(os.environ.get("FAL_KEY"))


def fal_generate_audio(endpoint: str, arguments: dict) -> bytes:
    """Call a fal audio endpoint and return the generated audio bytes.

    Raises on missing key, API error, or a response without an audio URL.
    """
    if not fal_available():
        raise RuntimeError("FAL_KEY is not set")

    import fal_client

    result = fal_client.subscribe(endpoint, arguments=arguments)
    url = (result.get("audio") or {}).get("url") if isinstance(result, dict) else None
    if not url:
        raise RuntimeError(f"fal endpoint {endpoint} returned no audio URL: {result!r}")

    response = httpx.get(url, timeout=120)
    response.raise_for_status()
    return response.content


def resolve_fal_voice(voice: str) -> str:
    """Translate a config voice value into fal's voice-name form.

    Accepts a preset name ("river"), a shared voice_id ("SAz9YHcvj6GT..."),
    or an already-correct fal name ("River").
    """
    lowered = voice.lower()
    if lowered in ElevenLabsTTSProvider.PRESET_VOICES:
        return lowered.title()
    if voice in _ID_TO_NAME:
        return _ID_TO_NAME[voice].title()
    return voice


def fal_sound_effect(
    prompt: str, seconds: float, loop: bool = False, output_format: str = "mp3_44100_128"
) -> bytes:
    """Generate one sound effect via fal (ElevenLabs Sound Effects V2)."""
    arguments = {
        "text": prompt,
        "duration_seconds": min(seconds, SFX_MAX_SECONDS),
        "prompt_influence": 0.5,
        "output_format": output_format,
    }
    if loop:
        arguments["loop"] = True
    return fal_generate_audio(SFX_ENDPOINT, arguments)


def fal_music(prompt: str, seconds: float, force_instrumental: bool = True) -> bytes:
    """Compose a short piece of music via fal (ElevenLabs Music)."""
    return fal_generate_audio(
        MUSIC_ENDPOINT,
        {
            "prompt": prompt,
            "music_length_ms": int(seconds * 1000),
            "force_instrumental": force_instrumental,
        },
    )


class FalTTSProvider(TTSProvider):
    """Text-to-speech using Eleven v3 served through fal.ai.

    Configuration in config.yaml:
        tts:
          fal:
            # voice defaults to the shared tts.elevenlabs.voice_id, resolved
            # to fal's voice-name form; override with a name here if needed.
            voice: "River"
            format: "mp3_44100_128"
            speed: 1.0
    """

    # Eleven v3 accepts up to 3,000 chars per request; produced-episode voice
    # segments are far shorter, so this rarely triggers chunking.
    MAX_CHARS = 3000

    def __init__(self, config: dict):
        super().__init__(config)

        self.fal_config = self.tts_config.get("fal", {})
        elevenlabs_config = self.tts_config.get("elevenlabs", {})

        # Voice choice is shared with the ElevenLabs provider so flipping
        # tts...provider between "fal" and "elevenlabs" needs no other edit.
        raw_voice = self.fal_config.get("voice") or elevenlabs_config.get("voice_id", "river")
        self.voice = resolve_fal_voice(raw_voice)

        self.endpoint = self.fal_config.get("endpoint", TTS_ENDPOINT)
        self.output_format = self.fal_config.get("format", "mp3_44100_128")
        self.speed = self.fal_config.get("speed", 1.0)
        self.stability = self.fal_config.get("stability")  # None => fal default

        self._available = fal_available()

    @property
    def name(self) -> str:
        return "fal.ai (ElevenLabs v3)"

    @property
    def max_chars(self) -> int:
        return self.MAX_CHARS

    @property
    def supported_formats(self) -> list[str]:
        return ["mp3_44100_128", "mp3_44100_192", "pcm_16000", "pcm_24000"]

    def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio via fal.

        Raises:
            RuntimeError: If no fal key is configured.
        """
        if not self._available:
            raise RuntimeError(
                "fal is not available. Set FAL_KEY and select a 'fal' provider in config."
            )

        chunks = self.chunk_text(text)
        if len(chunks) > 1:
            logger.info(f"  Text is {len(text)} chars, splitting into {len(chunks)} chunks")

        audio_parts = []
        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                logger.info(f"  Synthesizing chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...")

            arguments = {
                "text": chunk,
                "voice": self.voice,
                "output_format": self.output_format,
            }
            if self.speed and self.speed != 1.0:
                arguments["speed"] = self.speed
            if self.stability is not None:
                arguments["stability"] = self.stability

            audio_parts.append(fal_generate_audio(self.endpoint, arguments))

        return b"".join(audio_parts)
