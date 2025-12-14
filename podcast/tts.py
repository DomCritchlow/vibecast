"""Text-to-speech synthesis using OpenAI TTS API."""

import re
from openai import OpenAI


def preprocess_script_for_tts(script: str) -> str:
    """Preprocess the script for TTS synthesis.
    
    Handles pause markers and other formatting for better TTS output.
    
    Args:
        script: Raw script text with markers like [pause].
    
    Returns:
        Cleaned script ready for TTS.
    """
    # OpenAI TTS doesn't support SSML, but it handles natural pauses well
    # Convert [pause] markers to ellipsis or periods for natural pausing
    
    # Replace [pause] with a period and newline for a natural break
    processed = re.sub(r'\[pause\]', '.\n\n', script, flags=re.IGNORECASE)
    
    # Replace other potential markers
    processed = re.sub(r'\[slow\]', '', processed, flags=re.IGNORECASE)
    processed = re.sub(r'\[fast\]', '', processed, flags=re.IGNORECASE)
    processed = re.sub(r'\[breath\]', '.', processed, flags=re.IGNORECASE)
    
    # Clean up multiple newlines
    processed = re.sub(r'\n{3,}', '\n\n', processed)
    
    # Clean up multiple periods
    processed = re.sub(r'\.{2,}', '.', processed)
    
    # Clean up whitespace
    processed = processed.strip()
    
    return processed


def synthesize_mp3(script: str, config: dict) -> bytes:
    """Convert script to MP3 using OpenAI TTS.
    
    Args:
        script: The podcast script text.
        config: Full configuration dictionary.
    
    Returns:
        Raw MP3 bytes.
    """
    openai_config = config.get("openai", {})
    tts_config = openai_config.get("tts", {})
    
    # Preprocess the script
    processed_script = preprocess_script_for_tts(script)
    
    # Create OpenAI client (uses OPENAI_API_KEY env var)
    client = OpenAI()
    
    # Get TTS settings from config
    model = tts_config.get("model", "tts-1")
    voice = tts_config.get("voice", "nova")
    speed = tts_config.get("speed", 1.0)
    response_format = tts_config.get("format", "mp3")
    
    # Validate voice
    valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    if voice not in valid_voices:
        print(f"Warning: Invalid voice '{voice}', using 'nova'")
        voice = "nova"
    
    # Validate speed
    speed = max(0.25, min(4.0, float(speed)))
    
    # Validate model
    valid_models = ["tts-1", "tts-1-hd"]
    if model not in valid_models:
        print(f"Warning: Invalid model '{model}', using 'tts-1'")
        model = "tts-1"
    
    # Validate format
    valid_formats = ["mp3", "opus", "aac", "flac", "wav", "pcm"]
    if response_format not in valid_formats:
        print(f"Warning: Invalid format '{response_format}', using 'mp3'")
        response_format = "mp3"
    
    # Generate speech
    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=processed_script,
        speed=speed,
        response_format=response_format,
    )
    
    # Return raw audio bytes
    return response.content


def estimate_audio_duration(script: str, speed: float = 1.0) -> float:
    """Estimate the audio duration in minutes.
    
    Based on average speaking rate of ~150 words per minute.
    
    Args:
        script: The script text.
        speed: TTS speed multiplier.
    
    Returns:
        Estimated duration in minutes.
    """
    # Count words
    words = len(script.split())
    
    # Base rate: ~150 words per minute at normal speed
    base_wpm = 150
    
    # Adjust for speed
    effective_wpm = base_wpm * speed
    
    # Calculate duration
    duration_minutes = words / effective_wpm
    
    return duration_minutes


def get_voice_description(voice: str) -> str:
    """Get a human-readable description of an OpenAI TTS voice.
    
    Args:
        voice: Voice identifier.
    
    Returns:
        Description string.
    """
    descriptions = {
        "alloy": "Neutral and balanced - versatile for any content",
        "echo": "Warm and conversational - great for friendly content",
        "fable": "Expressive and dynamic - perfect for storytelling",
        "onyx": "Deep and authoritative - ideal for news/professional content",
        "nova": "Friendly and warm - excellent for upbeat, positive content",
        "shimmer": "Soft and gentle - best for calm, meditative content",
    }
    
    return descriptions.get(voice, "Unknown voice")


def list_available_voices() -> list[dict]:
    """List all available OpenAI TTS voices with descriptions.
    
    Returns:
        List of voice dictionaries with id and description.
    """
    return [
        {"id": "alloy", "description": get_voice_description("alloy")},
        {"id": "echo", "description": get_voice_description("echo")},
        {"id": "fable", "description": get_voice_description("fable")},
        {"id": "onyx", "description": get_voice_description("onyx")},
        {"id": "nova", "description": get_voice_description("nova")},
        {"id": "shimmer", "description": get_voice_description("shimmer")},
    ]

