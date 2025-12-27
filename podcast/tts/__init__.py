"""Text-to-speech providers for Vibecast."""

import re
from typing import Optional

from .base import TTSProvider, TTSResult
from .openai_tts import OpenAITTSProvider
from .elevenlabs import ElevenLabsTTSProvider

# Registry of available providers
PROVIDERS = {
    "openai": OpenAITTSProvider,
    "elevenlabs": ElevenLabsTTSProvider,
}


def get_tts_provider(config: dict) -> TTSProvider:
    """Factory function to get the configured TTS provider.
    
    Args:
        config: Full configuration dictionary.
    
    Returns:
        Configured TTSProvider instance.
    """
    tts_config = config.get("tts", {})
    provider_name = tts_config.get("provider", "openai")
    
    provider_class = PROVIDERS.get(provider_name)
    if not provider_class:
        print(f"Warning: Unknown TTS provider '{provider_name}', using 'openai'")
        provider_class = OpenAITTSProvider
    
    return provider_class(config)


def synthesize_speech(text: str, config: dict) -> bytes:
    """Convenience function to synthesize speech.
    
    Preprocesses text, uses the configured provider, and optionally
    applies audio post-processing.
    
    Args:
        text: Text to synthesize.
        config: Full configuration dictionary.
    
    Returns:
        Audio bytes (format depends on provider config).
    """
    # Preprocess the text
    processed = preprocess_for_tts(text)
    
    # Get provider and synthesize
    provider = get_tts_provider(config)
    audio_bytes = provider.synthesize(processed)
    
    # Apply audio post-processing if enabled
    tts_config = config.get("tts", {})
    audio_config = tts_config.get("audio_processing", {})
    
    if audio_config.get("enabled", False):
        try:
            from ..audio_processing import enhance_audio
            preset = audio_config.get("preset", "clarity")
            print(f"  Applying audio enhancement: {preset}")
            audio_bytes = enhance_audio(audio_bytes, preset=preset)
        except Exception as e:
            print(f"  Warning: Audio processing failed: {e}")
            print(f"  Using unprocessed audio")
    
    return audio_bytes


def preprocess_for_tts(text: str) -> str:
    """Preprocess text for TTS synthesis.
    
    Handles temperature symbols, pause markers, and other formatting
    for better TTS output. This is provider-agnostic.
    
    Args:
        text: Raw text with markers like [pause].
    
    Returns:
        Cleaned text ready for TTS.
    """
    processed = text
    
    # Expand temperature notation for natural speech
    processed = re.sub(r'(-?\d+)\s*°C\b', r'\1 degrees Celsius', processed)
    processed = re.sub(r'(-?\d+)\s*°F\b', r'\1 degrees Fahrenheit', processed)
    processed = re.sub(r'(-?\d+)\s*degrees?\s*C\b', r'\1 degrees Celsius', processed)
    processed = re.sub(r'(-?\d+)\s*degrees?\s*F\b', r'\1 degrees Fahrenheit', processed)
    
    # Expand other common symbols
    processed = re.sub(r'(\d+)\s*%', r'\1 percent', processed)
    processed = re.sub(r'(\d+)\s*km/h', r'\1 kilometers per hour', processed)
    processed = re.sub(r'(\d+)\s*mph', r'\1 miles per hour', processed)
    processed = re.sub(r'(\d+)\s*km\b', r'\1 kilometers', processed)
    processed = re.sub(r'(\d+)\s*mi\b', r'\1 miles', processed)
    
    # Handle pause markers
    processed = re.sub(r'\[pause\]', '.\n\n', processed, flags=re.IGNORECASE)
    processed = re.sub(r'\[slow\]', '', processed, flags=re.IGNORECASE)
    processed = re.sub(r'\[fast\]', '', processed, flags=re.IGNORECASE)
    processed = re.sub(r'\[breath\]', '.', processed, flags=re.IGNORECASE)
    
    # Clean up
    processed = re.sub(r'\n{3,}', '\n\n', processed)
    processed = re.sub(r'\.{2,}', '.', processed)
    processed = processed.strip()
    
    return processed


def estimate_duration(text: str, speed: float = 1.0) -> float:
    """Estimate audio duration in minutes.
    
    Args:
        text: The script text.
        speed: TTS speed multiplier.
    
    Returns:
        Estimated duration in minutes.
    """
    words = len(text.split())
    base_wpm = 150
    effective_wpm = base_wpm * speed
    return words / effective_wpm


