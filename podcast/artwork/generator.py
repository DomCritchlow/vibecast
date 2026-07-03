"""Main artwork generation orchestrator."""

import logging
from datetime import datetime
from typing import Any

from .base import ArtworkProvider
from .brief import generate_art_brief
from .openai_provider import OpenAIArtworkProvider
from .prompt import render_artwork_prompt

logger = logging.getLogger(__name__)

# Registry of available providers
PROVIDERS = {
    "openai": OpenAIArtworkProvider,
}


def get_artwork_provider(config: dict) -> ArtworkProvider:
    """Factory function to get the configured artwork provider."""
    artwork_config = config.get("artwork", {})
    provider_name = artwork_config.get("provider", "openai")

    provider_class = PROVIDERS.get(provider_name)
    if not provider_class:
        logger.warning("Unknown artwork provider '%s', using 'openai'", provider_name)
        provider_class = OpenAIArtworkProvider

    return provider_class(config)


def generate_and_publish_episode_artwork(
    episode_context: dict[str, Any],
    config: dict,
    storage_upload_fn=None,
    storage_metadata_fn=None,
    get_fallback_fn=None,
) -> tuple[str, str]:
    """Generate AI artwork for an episode and publish to R2.

    Orchestrates: art brief generation -> prompt rendering -> image
    generation -> R2 upload -> metadata storage. On any failure, returns the
    fallback artwork URL and default accent color.

    Args:
        episode_context: Dict with 'episode_id', 'items', 'title'.
        config: Full configuration dictionary.
        storage_upload_fn: Function to upload artwork to R2 (injected for testability).
        storage_metadata_fn: Function to upload metadata to R2 (injected for testability).
        get_fallback_fn: Function to get fallback URL (injected for testability).

    Returns:
        Tuple of (artwork_url, accent_color_name).
    """
    artwork_config = config.get("artwork", {})

    if not artwork_config.get("enabled", True):
        logger.info("Artwork generation is disabled")
        fallback_url = (
            get_fallback_fn(config) if get_fallback_fn else _get_default_fallback_url(config)
        )
        default_color = artwork_config.get("accent_palette", ["burnt orange"])[0]
        return fallback_url, default_color

    episode_id = episode_context.get("episode_id", datetime.now().strftime("%Y-%m-%d"))
    items = episode_context.get("items", [])

    logger.info("Generating AI artwork for episode %s", episode_id)

    try:
        brief = generate_art_brief(items, episode_id, config)
        logger.info(
            "Art brief: %s (accent: %s)", brief.single_scene_metaphor[:80], brief.accent_color
        )
        accent_color_used = brief.accent_color

        prompt, negative_prompt = render_artwork_prompt(brief, config)

        provider = get_artwork_provider(config)
        size = artwork_config.get("size", 1024)
        format = artwork_config.get("format", "png")

        logger.info("Generating image with %s", provider.name)

        retries = artwork_config.get("retries", 1)
        image_bytes = None
        last_error = None

        for attempt in range(retries + 1):
            try:
                image_bytes = provider.generate(
                    prompt=prompt,
                    size=size,
                    format=format,
                    negative_prompt=negative_prompt,
                )
                break
            except Exception as e:
                last_error = e
                if attempt < retries:
                    logger.warning("Attempt %d failed: %s, retrying...", attempt + 1, e)
                else:
                    raise

        if image_bytes is None:
            raise last_error or RuntimeError("Image generation returned no data")

        logger.info("Generated image: %d bytes", len(image_bytes))

        if storage_upload_fn:
            artwork_url = storage_upload_fn(episode_id, image_bytes, config)
        else:
            # Import here to avoid circular imports
            from ..storage import upload_artwork_to_r2

            artwork_url = upload_artwork_to_r2(episode_id, image_bytes, config)

        logger.info("Uploaded artwork to %s", artwork_url)

        if artwork_config.get("save_prompt_metadata", True):
            metadata = {
                "episode_id": episode_id,
                "generated_at": datetime.now().isoformat(),
                "provider": provider.name,
                "brief": brief.to_dict(),
                "size": size,
                "prompt_version": artwork_config.get("prompt_version", "v1"),
                "style": artwork_config.get("style", "vibecast_riso_v1"),
            }

            if storage_metadata_fn:
                storage_metadata_fn(episode_id, metadata, prompt, config)
            else:
                from ..storage import upload_artwork_metadata_to_r2

                upload_artwork_metadata_to_r2(episode_id, metadata, prompt, config)

        return artwork_url, accent_color_used

    except Exception as e:
        logger.error("Artwork generation failed: %s; using fallback artwork", e)
        fallback_url = (
            get_fallback_fn(config) if get_fallback_fn else _get_default_fallback_url(config)
        )
        default_color = artwork_config.get("accent_palette", ["burnt orange"])[0]
        return fallback_url, default_color


def _get_default_fallback_url(config: dict) -> str:
    """Get the fallback artwork URL from config."""
    from ..storage import get_fallback_artwork_url

    return get_fallback_artwork_url(config)
