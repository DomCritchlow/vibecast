"""Text-to-speech synthesis using OpenAI TTS API."""

import re
from openai import OpenAI

# OpenAI TTS API character limit
MAX_TTS_CHARS = 4096


def chunk_text(text: str, max_chars: int = MAX_TTS_CHARS) -> list[str]:
    """Split text into chunks that fit within the TTS character limit.
    
    Tries to split at natural break points (paragraphs, sentences) to avoid
    cutting off mid-sentence.
    
    Args:
        text: The text to split.
        max_chars: Maximum characters per chunk.
    
    Returns:
        List of text chunks.
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    remaining = text
    
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        
        # Find the best split point within the limit
        chunk = remaining[:max_chars]
        
        # Try to split at a paragraph break (double newline)
        split_pos = chunk.rfind('\n\n')
        
        # If no paragraph break, try sentence boundaries
        if split_pos == -1 or split_pos < max_chars // 2:
            # Look for sentence endings: . ! ? followed by space or newline
            for pattern in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                pos = chunk.rfind(pattern)
                if pos > split_pos and pos >= max_chars // 2:
                    split_pos = pos + 1  # Include the punctuation
        
        # If still no good split point, try comma or semicolon
        if split_pos == -1 or split_pos < max_chars // 2:
            for pattern in [', ', '; ', ',\n', ';\n']:
                pos = chunk.rfind(pattern)
                if pos > split_pos and pos >= max_chars // 2:
                    split_pos = pos + 1
        
        # Last resort: split at word boundary
        if split_pos == -1 or split_pos < max_chars // 2:
            split_pos = chunk.rfind(' ')
        
        # Absolute last resort: hard cut
        if split_pos == -1:
            split_pos = max_chars
        
        chunks.append(remaining[:split_pos].strip())
        remaining = remaining[split_pos:].strip()
    
    return [c for c in chunks if c]  # Filter out empty chunks


def preprocess_script_for_tts(script: str) -> str:
    """Preprocess the script for TTS synthesis.
    
    Handles pause markers, temperature symbols, and other formatting 
    for better TTS output.
    
    Args:
        script: Raw script text with markers like [pause].
    
    Returns:
        Cleaned script ready for TTS.
    """
    processed = script
    
    # Expand temperature notation for natural speech
    # Handle °C and °F (with degree symbol)
    processed = re.sub(r'(-?\d+)\s*°C\b', r'\1 degrees Celsius', processed)
    processed = re.sub(r'(-?\d+)\s*°F\b', r'\1 degrees Fahrenheit', processed)
    # Handle standalone degree symbol with C/F
    processed = re.sub(r'(-?\d+)\s*degrees?\s*C\b', r'\1 degrees Celsius', processed)
    processed = re.sub(r'(-?\d+)\s*degrees?\s*F\b', r'\1 degrees Fahrenheit', processed)
    
    # Expand other common symbols TTS may struggle with
    processed = re.sub(r'(\d+)\s*%', r'\1 percent', processed)
    processed = re.sub(r'(\d+)\s*km/h', r'\1 kilometers per hour', processed)
    processed = re.sub(r'(\d+)\s*mph', r'\1 miles per hour', processed)
    processed = re.sub(r'(\d+)\s*km\b', r'\1 kilometers', processed)
    processed = re.sub(r'(\d+)\s*mi\b', r'\1 miles', processed)
    
    # OpenAI TTS doesn't support SSML, but it handles natural pauses well
    # Convert [pause] markers to ellipsis or periods for natural pausing
    
    # Replace [pause] with a period and newline for a natural break
    processed = re.sub(r'\[pause\]', '.\n\n', processed, flags=re.IGNORECASE)
    
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
    
    Handles long scripts by chunking them into segments under the API's
    4096 character limit and concatenating the resulting audio.
    
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
    
    # Chunk the text to fit within API limits
    chunks = chunk_text(processed_script)
    
    if len(chunks) > 1:
        print(f"  Script is {len(processed_script)} chars, splitting into {len(chunks)} chunks")
    
    # Generate speech for each chunk
    audio_parts = []
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            print(f"  Synthesizing chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...")
        
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=chunk,
            speed=speed,
            response_format=response_format,
        )
        audio_parts.append(response.content)
    
    # Concatenate audio chunks
    # MP3 frames are independent, so simple concatenation works
    return b''.join(audio_parts)


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

