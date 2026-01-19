"""Art brief generation using LLM."""

import json
import hashlib
from typing import List

from openai import OpenAI

from .base import ArtBrief


def stable_hash(text: str) -> int:
    """Generate a stable hash from text for deterministic selection."""
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def select_accent_color(episode_id: str, config: dict) -> str:
    """Select accent color based on configuration strategy.
    
    Args:
        episode_id: Episode identifier (e.g., "2025-01-19").
        config: Full configuration dictionary.
    
    Returns:
        Selected accent color string.
    """
    artwork_config = config.get("artwork", {})
    palette = artwork_config.get("accent_palette", ["burnt orange"])
    strategy = artwork_config.get("accent_strategy", "rotate")
    
    if strategy == "fixed":
        return artwork_config.get("fixed_accent", palette[0])
    elif strategy == "random":
        import random
        return random.choice(palette)
    else:  # rotate
        idx = stable_hash(episode_id) % len(palette)
        return palette[idx]


def generate_art_brief(
    items: List,
    episode_id: str,
    config: dict,
) -> ArtBrief:
    """Generate an art direction brief from episode content.
    
    Uses GPT to analyze episode items and create a focused art brief
    with ONE scene metaphor and ONE secondary detail.
    
    Args:
        items: List of ContentItem objects from the episode.
        episode_id: Episode identifier for deterministic color selection.
        config: Full configuration dictionary.
    
    Returns:
        ArtBrief with scene description and styling info.
    """
    # Select accent color deterministically
    accent_color = select_accent_color(episode_id, config)
    
    # Build content summary for the LLM
    content_lines = []
    for i, item in enumerate(items[:6], 1):  # Use top 6 items
        content_lines.append(f"{i}) {item.title} — {item.source}")
    
    content_text = "\n".join(content_lines)
    
    # System prompt for brief generation
    system_prompt = """You create cover art briefs for a daily tech/science podcast.

CRITICAL CONSTRAINTS:
- ONE scene metaphor only. NOT a collage of multiple objects.
- The scene should be a single clear visual concept that captures the essence of today's stories.
- Include exactly ONE small secondary detail (a tiny symbolic element, not another full object).
- Think "editorial illustration" not "infographic".
- The scene should work as a risograph/screenprint poster - bold, simple shapes.

Return ONLY valid JSON with these exact fields:
{
  "mood_adjectives": ["word1", "word2", "word3"],
  "single_scene_metaphor": "A clear description of ONE scene/visual concept",
  "secondary_detail": "One small symbolic detail"
}

GOOD examples of single_scene_metaphor:
- "A lone astronaut floating above Earth, reaching toward a distant star"
- "A massive tree growing from an open book, its branches reaching into clouds"
- "A lighthouse beam cutting through digital fog"
- "An owl perched on a telescope, gazing at a glowing constellation"

BAD examples (too many objects, collage-like):
- "A rocket, a brain, a computer chip, and some gears arranged together"
- "Various tech items floating in space: laptop, phone, satellite"
- "A montage of today's news: AI chip, solar panel, Mars rover"

The secondary_detail should be small and subtle:
- "a tiny origami crane floating nearby"
- "a small compass in the corner"
- "a single fallen leaf"

NOT another main subject like "a person watching" or "a city in background"."""

    user_prompt = f"""Create an art brief for today's episode.

Episode items:
{content_text}

Create ONE cohesive visual metaphor that captures the spirit of these stories.
Do not enumerate the stories as separate objects.
Return valid JSON only."""

    # Get LLM settings
    openai_config = config.get("openai", {})
    llm_config = openai_config.get("llm", {})
    model = llm_config.get("model", "gpt-4o-mini")
    
    # Generate brief
    client = OpenAI()
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    
    # Parse response
    content = response.choices[0].message.content.strip()
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse art brief JSON: {e}")
        # Return a fallback brief
        return ArtBrief(
            mood_adjectives=["curious", "hopeful", "expansive"],
            single_scene_metaphor="A lone figure standing at the edge of a vast digital horizon, sunrise breaking through data clouds",
            secondary_detail="a small paper airplane drifting in the wind",
            accent_color=accent_color,
        )
    
    # Validate and extract fields
    mood = data.get("mood_adjectives", ["curious", "hopeful", "expansive"])
    if not isinstance(mood, list) or len(mood) < 2:
        mood = ["curious", "hopeful", "expansive"]
    
    scene = data.get("single_scene_metaphor", "")
    if not scene:
        scene = "A lone figure gazing at a glowing horizon where technology meets nature"
    
    detail = data.get("secondary_detail", "")
    if not detail:
        detail = "a small compass resting nearby"
    
    return ArtBrief(
        mood_adjectives=mood[:3],  # Limit to 3
        single_scene_metaphor=scene,
        secondary_detail=detail,
        accent_color=accent_color,
    )
