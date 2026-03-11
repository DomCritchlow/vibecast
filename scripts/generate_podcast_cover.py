#!/usr/bin/env python3
"""Generate new Vibecast podcast cover artwork using our Bento style."""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from podcast.artwork.openai_provider import OpenAIArtworkProvider


# Podcast cover prompt using our locked Bento style
COVER_PROMPT = """Editorial collage illustration in a modern risograph / screenprint poster style.
High-contrast cut-paper look: black ink + warm off-white paper + one accent color (burnt orange).
Halftone (Ben-Day) dot shading for clouds and shadows, visible paper grain, ink noise, subtle layer misregistration.
Bold simple shapes, strong negative space, graphic composition. Not a detailed illustration.

Single scene/metaphor:
A stylized sunrise breaking over the horizon. Bold geometric sun disc rising with dramatic halftone ray beams radiating outward. The rays use gradient halftone dots transitioning from dense to sparse. Simple silhouette of rolling hills or abstract landscape at the bottom.

Include exactly one secondary detail:
A single small bird silhouette in flight (one only)

Text element:
The word "VIBECAST" in bold, clean sans-serif typography centered near the top of the composition. The text should be in black ink, large and legible, in a modernist poster style.

Mood: optimistic, fresh, curious, inviting

Remove all other objects: no desks, no keyboards, no UI, no extra icons, no extra props, no busy background.
Square album cover composition suitable for a podcast."""

NEGATIVE_PROMPT = """busy composition, collage of multiple objects, computer keyboard, circuit board, UI elements, detailed background,
photorealism, 3D render, complex gradients, watermark, logo,
multiple main subjects, cluttered scene, realistic photo, photograph, complex shading, illegible text, distorted letters"""


def main():
    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Run: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    print("=" * 60)
    print("VIBECAST PODCAST COVER GENERATOR")
    print("Style: Risograph / Screenprint")
    print("Accent: Burnt Orange")
    print("=" * 60)
    print()
    
    # Create provider with minimal config
    config = {
        "artwork": {
            "provider": "openai",
            "model": "dall-e-3",
            "quality": "hd",
            "size": 1024,
        }
    }
    
    provider = OpenAIArtworkProvider(config)
    
    print("Generating podcast cover artwork...")
    print()
    print("Prompt preview:")
    print("-" * 40)
    print(COVER_PROMPT[:300] + "...")
    print("-" * 40)
    print()
    
    try:
        # Generate the image
        image_bytes = provider.generate(
            prompt=COVER_PROMPT,
            size=1024,
            format="png",
            seed=None,  # Random for variety
            negative_prompt=NEGATIVE_PROMPT,
        )
        
        print(f"Generated image: {len(image_bytes):,} bytes")
        
        # Save to docs/assets/images/
        output_dir = Path(__file__).parent.parent / "docs" / "assets" / "images"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / "podcast-cover.png"
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        
        print(f"Saved to: {output_path}")
        print()
        print("SUCCESS! New podcast cover generated.")
        print()
        print("Next steps:")
        print("1. Review the image at docs/assets/images/podcast-cover.png")
        print("2. If you like it, you can use it as your podcast artwork")
        print("3. Run again for a different variation")
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
