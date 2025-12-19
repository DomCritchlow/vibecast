"""Base class and types for episode image providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ImageResult:
    """Result from an image provider.
    
    Attributes:
        image_url: URL to the image (original source).
        title: Title or description of the image.
        credit: Attribution/copyright information.
        source: Name of the source (e.g., "nasa_apod", "unsplash").
    """
    image_url: str
    title: str
    credit: str
    source: str


class ImageProvider(ABC):
    """Abstract base class for episode image providers.
    
    Implement this class to add new image sources like Unsplash, Pexels, etc.
    
    Example:
        class UnsplashImageProvider(ImageProvider):
            def get_image(self) -> Optional[ImageResult]:
                # Fetch from Unsplash API
                return ImageResult(
                    image_url="https://...",
                    title="Beautiful sunrise",
                    credit="Photo by John Doe on Unsplash",
                    source="unsplash"
                )
    """
    
    def __init__(self, config: dict):
        """Initialize the provider with configuration.
        
        Args:
            config: Full configuration dictionary.
        """
        self.config = config
        self.image_config = config.get("sources", {}).get("episode_image", {})
    
    @abstractmethod
    def get_image(self) -> Optional[ImageResult]:
        """Fetch an image for today's episode.
        
        Returns:
            ImageResult with image data, or None if unavailable.
        """
        pass
    
    @property
    def name(self) -> str:
        """Human-readable name of this provider."""
        return self.__class__.__name__.replace("ImageProvider", "")

