"""OpenAI TTS provider."""

import subprocess
import tempfile
import os
from typing import List
from openai import OpenAI

from .base import TTSProvider


class OpenAITTSProvider(TTSProvider):
    """Text-to-speech using OpenAI's TTS API.
    
    Supports models: tts-1 (fast), tts-1-hd (high quality)
    Voices: alloy, echo, fable, onyx, nova, shimmer
    
    IMPORTANT: OpenAI outputs MP3 at only 24kHz/128kbps which sounds bad.
    This provider uses OPUS (48kHz) internally and converts to high-quality
    MP3 (44.1kHz/192kbps) for much better audio quality.
    
    Configuration in config.yaml:
        tts:
          provider: "openai"
          openai:
            model: "tts-1"
            voice: "nova"
            speed: 0.95
            format: "mp3"  # Output format (conversion handled automatically)
    """
    
    # All 13 available voices
    VALID_VOICES = [
        "alloy", "ash", "ballad", "cedar", "coral", "echo", 
        "fable", "marin", "nova", "onyx", "sage", "shimmer", "verse"
    ]
    
    # Available models
    VALID_MODELS = [
        "tts-1", "tts-1-hd",
        "gpt-4o-mini-tts",
        "gpt-4o-mini-tts-2025-12-15",
        "gpt-4o-mini-tts-2025-03-20",
    ]
    
    VALID_FORMATS = ["mp3", "opus", "aac", "flac", "wav", "pcm"]
    MAX_CHARS = 4096
    
    # Note: marin and cedar are recommended for best quality
    # Note: ballad, cedar, marin, verse only work with gpt-4o-mini-tts
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.openai_config = self.tts_config.get("openai", {})
        
        # Get settings with validation
        self.model = self._validate_model(self.openai_config.get("model", "tts-1"))
        self.voice = self._validate_voice(self.openai_config.get("voice", "nova"))
        self.speed = self._validate_speed(self.openai_config.get("speed", 1.0))
        self.format = self._validate_format(self.openai_config.get("format", "mp3"))
        self.instructions = self.openai_config.get("instructions")  # Optional instructions parameter
        
        # High-quality output settings
        # OpenAI's MP3 output is only 24kHz/128kbps. We request OPUS (48kHz)
        # and convert to high-quality MP3 (44.1kHz/192kbps) for much better audio.
        self.hq_sample_rate = 44100  # 44.1kHz - CD quality
        self.hq_bitrate = "192k"     # 192kbps - high quality MP3
        
        # Check ffmpeg availability
        self._ffmpeg_available = self._check_ffmpeg()
        
        # Create client
        self.client = OpenAI()
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available for audio conversion."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Warning: ffmpeg not found. Audio quality will be degraded (24kHz/128kbps).")
            return False
    
    def _validate_model(self, model: str) -> str:
        if model not in self.VALID_MODELS:
            print(f"Warning: Invalid OpenAI model '{model}', using 'tts-1'")
            return "tts-1"
        return model
    
    def _validate_voice(self, voice: str) -> str:
        if voice not in self.VALID_VOICES:
            print(f"Warning: Invalid OpenAI voice '{voice}', using 'nova'")
            return "nova"
        return voice
    
    def _validate_speed(self, speed: float) -> float:
        return max(0.25, min(4.0, float(speed)))
    
    def _validate_format(self, fmt: str) -> str:
        if fmt not in self.VALID_FORMATS:
            print(f"Warning: Invalid format '{fmt}', using 'mp3'")
            return "mp3"
        return fmt
    
    @property
    def name(self) -> str:
        return "OpenAI TTS"
    
    @property
    def max_chars(self) -> int:
        return self.MAX_CHARS
    
    @property
    def supported_formats(self) -> List[str]:
        return self.VALID_FORMATS
    
    def _convert_opus_to_mp3(self, opus_bytes: bytes) -> bytes:
        """Convert OPUS audio to high-quality MP3.
        
        OPUS from OpenAI is 48kHz. We convert to 44.1kHz/192kbps MP3
        which is much better than OpenAI's native MP3 (24kHz/128kbps).
        
        Args:
            opus_bytes: OPUS audio data from OpenAI.
            
        Returns:
            High-quality MP3 bytes.
        """
        with tempfile.NamedTemporaryFile(suffix=".opus", delete=False) as opus_file:
            opus_file.write(opus_bytes)
            opus_path = opus_file.name
        
        mp3_path = opus_path.replace(".opus", ".mp3")
        
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", opus_path,
                "-ar", str(self.hq_sample_rate),  # 44.1kHz
                "-b:a", self.hq_bitrate,          # 192kbps
                "-f", "mp3",
                mp3_path,
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                print(f"Warning: ffmpeg conversion failed, using raw OPUS")
                return opus_bytes
            
            with open(mp3_path, "rb") as f:
                mp3_bytes = f.read()
            
            return mp3_bytes
            
        finally:
            # Cleanup temp files
            if os.path.exists(opus_path):
                os.unlink(opus_path)
            if os.path.exists(mp3_path):
                os.unlink(mp3_path)
    
    def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio using OpenAI TTS.
        
        Handles long texts by chunking and concatenating.
        
        For best quality, we request OPUS (48kHz) from OpenAI and convert
        to high-quality MP3 (44.1kHz/192kbps). This sounds MUCH better than
        OpenAI's native MP3 output (24kHz/128kbps).
        """
        chunks = self.chunk_text(text)
        
        if len(chunks) > 1:
            print(f"  Text is {len(text)} chars, splitting into {len(chunks)} chunks")
        
        # Determine if we should use OPUS->MP3 conversion for better quality
        use_hq_conversion = (
            self._ffmpeg_available and 
            self.format == "mp3"
        )
        
        if use_hq_conversion:
            print(f"  Using high-quality mode: OPUS (48kHz) → MP3 (44.1kHz/192kbps)")
        
        audio_parts = []
        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                print(f"  Synthesizing chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...")
            
            # Build request parameters
            # Request OPUS for HQ mode (48kHz), otherwise use configured format
            request_format = "opus" if use_hq_conversion else self.format
            
            params = {
                "model": self.model,
                "voice": self.voice,
                "input": chunk,
                "speed": self.speed,
                "response_format": request_format,
            }
            
            # Add instructions if provided (only works with gpt-4o-mini-tts)
            if self.instructions:
                params["instructions"] = self.instructions
            
            response = self.client.audio.speech.create(**params)
            audio_bytes = response.content
            
            # Convert OPUS to high-quality MP3 if in HQ mode
            if use_hq_conversion:
                audio_bytes = self._convert_opus_to_mp3(audio_bytes)
            
            audio_parts.append(audio_bytes)
        
        # Concatenate audio chunks (MP3 frames are independent)
        return b''.join(audio_parts)


def get_voice_description(voice: str) -> str:
    """Get a human-readable description of an OpenAI TTS voice."""
    descriptions = {
        "alloy": "Neutral and balanced - versatile for any content",
        "echo": "Warm and conversational - great for friendly content",
        "fable": "Expressive and dynamic - perfect for storytelling",
        "onyx": "Deep and authoritative - ideal for news/professional content",
        "nova": "Friendly and warm - excellent for upbeat, positive content",
        "shimmer": "Soft and gentle - best for calm, meditative content",
    }
    return descriptions.get(voice, "Unknown voice")


