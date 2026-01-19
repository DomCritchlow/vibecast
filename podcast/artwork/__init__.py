"""AI-powered episode artwork generation for Vibecast.

This module generates unique cover art for each episode using OpenAI's
DALL-E 3 image generation API in an editorial risograph/screenprint style.

Usage:
    from podcast.artwork import generate_and_publish_episode_artwork
    
    episode_context = {
        "episode_id": "2025-01-19",
        "items": selected_items,
        "title": episode_title,
    }
    artwork_url = generate_and_publish_episode_artwork(episode_context, config)
"""

from .base import ArtBrief, ArtworkResult, ArtworkProvider
from .generator import (
    generate_and_publish_episode_artwork,
    get_artwork_provider,
)
from .brief import generate_art_brief, select_accent_color
from .prompt import render_artwork_prompt

__all__ = [
    # Main entry point
    "generate_and_publish_episode_artwork",
    
    # Types
    "ArtBrief",
    "ArtworkResult",
    "ArtworkProvider",
    
    # Lower-level functions
    "get_artwork_provider",
    "generate_art_brief",
    "select_accent_color",
    "render_artwork_prompt",
]
