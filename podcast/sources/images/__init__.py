"""Episode image providers for Vibecast."""

from typing import Optional

from .base import ImageProvider, ImageResult
from .nasa import NasaImageProvider

# Registry of available providers
PROVIDERS = {
    "nasa": NasaImageProvider,
}


def get_image_provider(config: dict) -> ImageProvider:
    """Factory function to get the configured image provider.
    
    Args:
        config: Full configuration dictionary.
    
    Returns:
        Configured ImageProvider instance.
    """
    sources = config.get("sources", {})
    image_config = sources.get("episode_image", {})
    provider_name = image_config.get("provider", "nasa")
    
    provider_class = PROVIDERS.get(provider_name)
    if not provider_class:
        print(f"Warning: Unknown image provider '{provider_name}', using 'nasa'")
        provider_class = NasaImageProvider
    
    return provider_class(config)


def get_episode_image(config: dict) -> Optional[ImageResult]:
    """Convenience function to get an episode image.
    
    Args:
        config: Full configuration dictionary.
    
    Returns:
        ImageResult with image data, or None if unavailable.
    """
    provider = get_image_provider(config)
    return provider.get_image()

