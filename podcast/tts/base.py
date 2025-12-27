"""Base class and types for TTS providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class TTSResult:
    """Result from a TTS provider.
    
    Attributes:
        audio_bytes: Raw audio data.
        format: Audio format (mp3, wav, etc.).
        duration_seconds: Estimated duration (if known).
    """
    audio_bytes: bytes
    format: str
    duration_seconds: Optional[float] = None


class TTSProvider(ABC):
    """Abstract base class for TTS providers.
    
    Implement this class to add new TTS services like ElevenLabs, Google, etc.
    
    Example:
        class GoogleTTSProvider(TTSProvider):
            def synthesize(self, text: str) -> bytes:
                # Call Google Cloud TTS API
                return audio_bytes
    """
    
    # Default chunk size for providers with character limits
    DEFAULT_MAX_CHARS = 4096
    
    def __init__(self, config: dict):
        """Initialize the provider with configuration.
        
        Args:
            config: Full configuration dictionary.
        """
        self.config = config
        self.tts_config = config.get("tts", {})
    
    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio.
        
        Implementations should handle chunking if the text exceeds
        the provider's limits.
        
        Args:
            text: Preprocessed text to synthesize.
        
        Returns:
            Raw audio bytes.
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this provider."""
        pass
    
    @property
    def max_chars(self) -> int:
        """Maximum characters per API request."""
        return self.DEFAULT_MAX_CHARS
    
    @property
    def supported_formats(self) -> List[str]:
        """Supported output audio formats."""
        return ["mp3"]
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks that fit within the provider's limits.
        
        Tries to split at natural break points (paragraphs, sentences).
        
        Args:
            text: The text to split.
        
        Returns:
            List of text chunks.
        """
        max_chars = self.max_chars
        
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        remaining = text
        
        while remaining:
            if len(remaining) <= max_chars:
                chunks.append(remaining)
                break
            
            chunk = remaining[:max_chars]
            split_pos = chunk.rfind('\n\n')
            
            if split_pos == -1 or split_pos < max_chars // 2:
                for pattern in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                    pos = chunk.rfind(pattern)
                    if pos > split_pos and pos >= max_chars // 2:
                        split_pos = pos + 1
            
            if split_pos == -1 or split_pos < max_chars // 2:
                for pattern in [', ', '; ', ',\n', ';\n']:
                    pos = chunk.rfind(pattern)
                    if pos > split_pos and pos >= max_chars // 2:
                        split_pos = pos + 1
            
            if split_pos == -1 or split_pos < max_chars // 2:
                split_pos = chunk.rfind(' ')
            
            if split_pos == -1:
                split_pos = max_chars
            
            chunks.append(remaining[:split_pos].strip())
            remaining = remaining[split_pos:].strip()
        
        return [c for c in chunks if c]


