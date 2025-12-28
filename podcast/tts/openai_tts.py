"""OpenAI TTS provider."""

from typing import List
from openai import OpenAI

from .base import TTSProvider


class OpenAITTSProvider(TTSProvider):
    """Text-to-speech using OpenAI's TTS API.
    
    Supports models: tts-1 (fast), tts-1-hd (high quality)
    Voices: alloy, echo, fable, onyx, nova, shimmer
    
    Configuration in config.yaml:
        tts:
          provider: "openai"
          openai:
            model: "tts-1"
            voice: "nova"
            speed: 0.95
            format: "mp3"
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
        self.format = self._validate_format(self.openai_config.get("format", "flac"))  # Default to FLAC for quality
        self.instructions = self.openai_config.get("instructions")  # Optional instructions parameter
        
        # Create client
        self.client = OpenAI()
    
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
    
    def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio using OpenAI TTS.
        
        Handles long texts by chunking and concatenating.
        """
        chunks = self.chunk_text(text)
        
        if len(chunks) > 1:
            print(f"  Text is {len(text)} chars, splitting into {len(chunks)} chunks")
        
        audio_parts = []
        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                print(f"  Synthesizing chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...")
            
            # Build request parameters
            params = {
                "model": self.model,
                "voice": self.voice,
                "input": chunk,
                "speed": self.speed,
                "response_format": self.format,
            }
            
            # Add instructions if provided (only works with gpt-4o-mini-tts)
            if self.instructions:
                params["instructions"] = self.instructions
            
            response = self.client.audio.speech.create(**params)
            audio_parts.append(response.content)
        
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


