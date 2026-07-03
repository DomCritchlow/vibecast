"""Art brief generation using the configured script writer LLM."""

import hashlib
import logging

from ..writer import get_writer
from .base import ArtBrief

logger = logging.getLogger(__name__)

BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "mood_adjectives": {
            "type": "array",
            "items": {"type": "string"},
        },
        "single_scene_metaphor": {"type": "string"},
        "secondary_detail": {"type": "string"},
    },
    "required": ["mood_adjectives", "single_scene_metaphor", "secondary_detail"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You create cover art briefs for a daily tech/science podcast.

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

FALLBACK_BRIEF = {
    "mood_adjectives": ["curious", "hopeful", "expansive"],
    "single_scene_metaphor": (
        "A lone figure standing at the edge of a vast digital horizon, "
        "sunrise breaking through data clouds"
    ),
    "secondary_detail": "a small paper airplane drifting in the wind",
}


def stable_hash(text: str) -> int:
    """Generate a stable hash from text for deterministic selection."""
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def select_accent_color(episode_id: str, config: dict) -> str:
    """Select accent color based on configuration strategy."""
    artwork_config = config.get("artwork", {})
    palette = artwork_config.get("accent_palette", ["burnt orange"])
    strategy = artwork_config.get("accent_strategy", "rotate")

    if strategy == "fixed":
        return artwork_config.get("fixed_accent", palette[0])
    elif strategy == "random":
        import random

        return random.choice(palette)
    else:  # rotate
        return palette[stable_hash(episode_id) % len(palette)]


def generate_art_brief(items: list, episode_id: str, config: dict) -> ArtBrief:
    """Generate an art direction brief from episode content.

    Uses the configured writer LLM to analyze episode items and create a
    focused art brief with ONE scene metaphor and ONE secondary detail.
    """
    accent_color = select_accent_color(episode_id, config)

    content_text = "\n".join(
        f"{i}) {item.title} — {item.source}" for i, item in enumerate(items[:6], 1)
    )

    user_prompt = f"""Create an art brief for today's episode.

Episode items:
{content_text}

Create ONE cohesive visual metaphor that captures the spirit of these stories.
Do not enumerate the stories as separate objects.
Return valid JSON only."""

    try:
        writer = get_writer(config)
        data = writer.generate_json(SYSTEM_PROMPT, user_prompt, BRIEF_SCHEMA, max_tokens=1000)
    except Exception as e:
        logger.warning("Art brief generation failed (%s); using fallback brief", e)
        data = FALLBACK_BRIEF

    mood = data.get("mood_adjectives") or FALLBACK_BRIEF["mood_adjectives"]
    if not isinstance(mood, list) or len(mood) < 2:
        mood = FALLBACK_BRIEF["mood_adjectives"]

    return ArtBrief(
        mood_adjectives=mood[:3],
        single_scene_metaphor=data.get("single_scene_metaphor")
        or FALLBACK_BRIEF["single_scene_metaphor"],
        secondary_detail=data.get("secondary_detail") or FALLBACK_BRIEF["secondary_detail"],
        accent_color=accent_color,
    )
