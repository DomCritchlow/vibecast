"""Main artwork generation orchestrator."""

import json
from typing import Dict, Any, Optional
from datetime import datetime

from .base import ArtBrief, ArtworkResult, ArtworkProvider
from .brief import generate_art_brief, stable_hash
from .prompt import render_artwork_prompt
from .openai_provider import OpenAIArtworkProvider


# Registry of available providers
PROVIDERS = {
    "openai": OpenAIArtworkProvider,
}


def get_artwork_provider(config: dict) -> ArtworkProvider:
    """Factory function to get the configured artwork provider.
    
    Args:
        config: Full configuration dictionary.
    
    Returns:
        Configured ArtworkProvider instance.
    """
    artwork_config = config.get("artwork", {})
    provider_name = artwork_config.get("provider", "openai")
    
    provider_class = PROVIDERS.get(provider_name)
    if not provider_class:
        print(f"Warning: Unknown artwork provider '{provider_name}', using 'openai'")
        provider_class = OpenAIArtworkProvider
    
    return provider_class(config)


def select_seed(episode_id: str, config: dict) -> Optional[int]:
    """Select generation seed based on configuration strategy.
    
    Note: DALL-E 3 doesn't support seeds, but we generate one anyway
    for metadata/logging purposes and future provider support.
    
    Args:
        episode_id: Episode identifier (e.g., "2025-01-19").
        config: Full configuration dictionary.
    
    Returns:
        Selected seed value, or None for random.
    """
    artwork_config = config.get("artwork", {})
    strategy = artwork_config.get("seed_strategy", "date")
    
    if strategy == "fixed":
        return artwork_config.get("fixed_seed", 12345)
    elif strategy == "random":
        return None
    else:  # date
        return stable_hash(episode_id)


def generate_and_publish_episode_artwork(
    episode_context: Dict[str, Any],
    config: dict,
    storage_upload_fn=None,
    storage_metadata_fn=None,
    get_fallback_fn=None,
) -> tuple[str, str]:
    """Generate AI artwork for an episode and publish to R2.
    
    This is the main entry point that orchestrates:
    1. Art brief generation (Step A)
    2. Prompt rendering (Step B)
    3. Image generation
    4. R2 upload
    5. Metadata storage
    
    On any failure, returns the fallback artwork URL and default accent color.
    
    Args:
        episode_context: Dict with 'episode_id', 'items', 'title'.
        config: Full configuration dictionary.
        storage_upload_fn: Function to upload artwork to R2 (injected for testability).
        storage_metadata_fn: Function to upload metadata to R2 (injected for testability).
        get_fallback_fn: Function to get fallback URL (injected for testability).
    
    Returns:
        Tuple of (artwork_url, accent_color_name) where accent_color_name is the color used in generation.
    """
    artwork_config = config.get("artwork", {})
    
    # Check if artwork generation is enabled
    if not artwork_config.get("enabled", True):
        print("  Artwork generation is disabled")
        fallback_url = get_fallback_fn(config) if get_fallback_fn else _get_default_fallback_url(config)
        default_color = artwork_config.get("accent_palette", ["burnt orange"])[0]
        return fallback_url, default_color
    
    episode_id = episode_context.get("episode_id", datetime.now().strftime("%Y-%m-%d"))
    items = episode_context.get("items", [])
    
    print(f"  Generating AI artwork for episode {episode_id}...")
    
    try:
        # Step A: Generate art brief from episode content
        print("  Step A: Generating art brief...")
        brief = generate_art_brief(items, episode_id, config)
        print(f"    Scene: {brief.single_scene_metaphor[:60]}...")
        print(f"    Accent: {brief.accent_color}")
        
        # Store the accent color for return
        accent_color_used = brief.accent_color
        
        # Step B: Render the final prompt
        print("  Step B: Rendering artwork prompt...")
        prompt, negative_prompt = render_artwork_prompt(brief, config)
        
        # Get provider and generation settings
        provider = get_artwork_provider(config)
        size = artwork_config.get("size", 1024)
        format = artwork_config.get("format", "png")
        seed = select_seed(episode_id, config)
        
        print(f"  Generating image with {provider.name}...")
        
        # Generate the image
        retries = artwork_config.get("retries", 1)
        image_bytes = None
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                image_bytes = provider.generate(
                    prompt=prompt,
                    size=size,
                    format=format,
                    seed=seed,
                    negative_prompt=negative_prompt,
                )
                break
            except Exception as e:
                last_error = e
                if attempt < retries:
                    print(f"    Attempt {attempt + 1} failed: {e}, retrying...")
                else:
                    raise
        
        if image_bytes is None:
            raise last_error or Exception("Image generation returned no data")
        
        print(f"    Generated image: {len(image_bytes)} bytes")
        
        # Upload to R2
        if storage_upload_fn:
            artwork_url = storage_upload_fn(episode_id, image_bytes, config)
        else:
            # Import here to avoid circular imports
            from ..storage import upload_artwork_to_r2
            artwork_url = upload_artwork_to_r2(episode_id, image_bytes, config)
        
        print(f"    Uploaded to: {artwork_url}")
        
        # Save metadata if enabled
        if artwork_config.get("save_prompt_metadata", True):
            metadata = {
                "episode_id": episode_id,
                "generated_at": datetime.now().isoformat(),
                "provider": provider.name,
                "brief": brief.to_dict(),
                "seed": seed,
                "size": size,
                "prompt_version": artwork_config.get("prompt_version", "v1"),
                "style": artwork_config.get("style", "vibecast_riso_v1"),
            }
            
            if storage_metadata_fn:
                storage_metadata_fn(episode_id, metadata, prompt, config)
            else:
                from ..storage import upload_artwork_metadata_to_r2
                upload_artwork_metadata_to_r2(episode_id, metadata, prompt, config)
            
            print("    Saved artwork metadata")
        
        return artwork_url, accent_color_used
    
    except Exception as e:
        print(f"  ERROR: Artwork generation failed: {e}")
        print("  Using fallback artwork...")
        
        fallback_url = get_fallback_fn(config) if get_fallback_fn else _get_default_fallback_url(config)
        default_color = artwork_config.get("accent_palette", ["burnt orange"])[0]
        return fallback_url, default_color


def _get_default_fallback_url(config: dict) -> str:
    """Get the fallback artwork URL from config.
    
    Args:
        config: Full configuration dictionary.
    
    Returns:
        Fallback artwork public URL.
    """
    # Try to import storage function
    try:
        from ..storage import get_fallback_artwork_url
        return get_fallback_artwork_url(config)
    except ImportError:
        # Construct URL manually as last resort
        storage_config = config.get("storage", {})
        r2_config = storage_config.get("r2", {})
        public_base_url = r2_config.get("public_base_url", "")
        artwork_config = config.get("artwork", {})
        fallback_key = artwork_config.get("r2_fallback_key", "static/default-episode-art.png")
        
        if public_base_url:
            return f"{public_base_url.rstrip('/')}/{fallback_key}"
        return ""
