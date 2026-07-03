"""Artwork prompt template rendering."""

from .base import ArtBrief

# Locked style prompt template for Vibecast editorial risograph aesthetic
STYLE_TEMPLATE_V1 = """Editorial collage illustration in a modern risograph / screenprint poster style.
High-contrast cut-paper look: black ink + warm off-white paper + one accent color ({accent_color}).
Halftone (Ben-Day) dot shading for clouds and shadows, visible paper grain, ink noise, subtle layer misregistration.
Bold simple shapes, strong negative space, graphic composition. Not a detailed illustration.

Single scene/metaphor:
{single_scene_metaphor}

Include exactly one secondary detail:
{secondary_detail} (one only)

Mood: {mood}

Remove all other objects: no desks, no keyboards, no UI, no extra icons, no extra props, no busy background.
No text, no letters, no logos, no watermark. Square album cover composition."""


# Negative prompt for providers that support it
NEGATIVE_PROMPT_V1 = """busy composition, collage of multiple objects, computer keyboard, circuit board, UI elements, detailed background,
photorealism, 3D render, complex gradients, text, typography, watermark, logo, words, letters,
multiple main subjects, cluttered scene, realistic photo, photograph, complex shading"""


def render_artwork_prompt(brief: ArtBrief, config: dict) -> tuple[str, str]:
    """Render the final artwork prompt from an art brief.

    Uses the locked style template to ensure consistent risograph aesthetic.

    Args:
        brief: ArtBrief with scene description and styling info.
        config: Full configuration dictionary.

    Returns:
        Tuple of (positive_prompt, negative_prompt).
    """
    artwork_config = config.get("artwork", {})
    prompt_version = artwork_config.get("prompt_version", "v1")

    # Select template based on version
    if prompt_version == "v1":
        template = STYLE_TEMPLATE_V1
        negative = NEGATIVE_PROMPT_V1
    else:
        # Default to v1
        template = STYLE_TEMPLATE_V1
        negative = NEGATIVE_PROMPT_V1

    # Format mood adjectives
    mood_str = ", ".join(brief.mood_adjectives)

    # Render the template
    prompt = template.format(
        accent_color=brief.accent_color,
        single_scene_metaphor=brief.single_scene_metaphor,
        secondary_detail=brief.secondary_detail,
        mood=mood_str,
    )

    return prompt, negative


def get_style_summary(config: dict) -> str:
    """Get a human-readable summary of the current style settings.

    Args:
        config: Full configuration dictionary.

    Returns:
        Style description string.
    """
    artwork_config = config.get("artwork", {})
    style = artwork_config.get("style", "vibecast_riso_v1")
    prompt_version = artwork_config.get("prompt_version", "v1")

    return f"Style: {style}, Prompt version: {prompt_version}"
