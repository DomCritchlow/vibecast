#!/usr/bin/env python3
"""Regenerate Vibecast brand artwork with the current image model (gpt-image-2).

Covers the three static images that episode art already outgrew:
  cover    - podcast show cover (VIBECAST wordmark) -> docs/artwork.png
             + docs/assets/images/podcast-cover.png
  default  - fallback episode art (no text)         -> docs/default-episode-art.png
  host     - Bento host portrait                    -> docs/assets/images/Vibecast_Host.png

Usage:
    uv run python scripts/generate_brand_art.py --asset all
    uv run python scripts/generate_brand_art.py --asset cover
    uv run python scripts/generate_brand_art.py --asset default --upload-fallback

Requires OPENAI_API_KEY; --upload-fallback additionally needs R2_* credentials.
Run via the "Regenerate Brand Artwork" GitHub Actions workflow if you don't
have keys locally.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from podcast.artwork.openai_provider import OpenAIArtworkProvider

REPO_ROOT = Path(__file__).parent.parent
DOCS = REPO_ROOT / "docs"
IMAGES = DOCS / "assets" / "images"

# Shared style block - the locked Vibecast riso aesthetic, with the extra
# craft language gpt-image-2 actually honors (fine grain, tonal depth).
RISO_STYLE = """Editorial illustration in a modern risograph / screenprint poster style.
High-contrast cut-paper look: black ink + warm off-white paper + one accent color (burnt orange).
Fine-grain halftone (Ben-Day) dot shading with smooth density gradients, visible paper grain,
ink speckle, subtle layer misregistration. Bold simple shapes, strong negative space,
dramatic tonal depth, confident graphic composition. Printmaking texture, not digital smoothness."""

COVER_PROMPT = f"""{RISO_STYLE}

Podcast cover art, square album composition.

Single scene/metaphor:
A stylized sunrise breaking over the horizon. A bold geometric sun disc rising with dramatic
halftone ray beams radiating outward — the rays transition from dense to sparse dots as they
travel. Black silhouetted rolling hills across the bottom with fine stipple texture. One or two
halftone clouds catching the light.

Include exactly one secondary detail:
A single small bird silhouette in flight (one only).

Text element:
The word "VIBECAST" in bold, clean grotesque sans-serif capitals, black ink, centered near the
top of the composition, modernist poster typography with a hint of print texture. Large, crisp,
and legible — it must still read clearly at small podcast-app thumbnail size.

Mood: optimistic, fresh, curious, inviting.

No other objects, no UI, no extra icons, no busy background, no other text."""

DEFAULT_ART_PROMPT = f"""{RISO_STYLE}

Square album cover composition for a daily podcast called "Morning Thread".

Single scene/metaphor:
A single luminous thread unspooling from a small spool in the foreground, drifting in one
elegant continuous line across a pre-dawn sky toward a halftone sun cresting the horizon.
The thread glows in burnt orange against deep black-ink hills and a warm paper sky.

Include exactly one secondary detail:
A single small bird silhouette perched on the thread (one only).

Mood: calm, curious, hopeful, early-morning.

No text, no letters, no logos, no watermark. No other objects, no busy background."""

HOST_PROMPT = f"""{RISO_STYLE}

Portrait-style square illustration of a podcast host.

Single scene/metaphor:
A friendly host with warm brown skin and wavy dark hair under a cream baseball cap, wearing
large studio headphones and a burnt-orange sweater, smiling as they speak into a broadcast
microphone on a boom arm. One hand holds a cream coffee mug. Behind them, a window with
halftone morning clouds and a small potted plant on the sill. Waist-up, facing slightly
off-camera.

Mood: warm, welcoming, curious, morning-energy.

No text, no letters, no logos, no watermark. Keep the scene simple — no extra props, no UI,
no cluttered desk."""

ASSETS = {
    "cover": {
        "prompt": COVER_PROMPT,
        "size": 1536,
        "outputs": [DOCS / "artwork.png", IMAGES / "podcast-cover.png"],
    },
    "default": {
        "prompt": DEFAULT_ART_PROMPT,
        "size": 1536,
        "outputs": [DOCS / "default-episode-art.png"],
    },
    "host": {
        "prompt": HOST_PROMPT,
        "size": 1024,
        "outputs": [IMAGES / "Vibecast_Host.png"],
    },
}


def generate_asset(provider: OpenAIArtworkProvider, name: str) -> bytes:
    spec = ASSETS[name]
    print(f"\n=== Generating '{name}' ({spec['size']}x{spec['size']}) ===")
    image_bytes = provider.generate(prompt=spec["prompt"], size=spec["size"], format="png")
    print(f"  Generated {len(image_bytes):,} bytes")
    for path in spec["outputs"]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes)
        print(f"  Saved {path.relative_to(REPO_ROOT)}")
    return image_bytes


def upload_fallback(image_bytes: bytes) -> None:
    from podcast.run_daily import load_config
    from podcast.storage import check_r2_connection, upload_fallback_artwork_to_r2

    config = load_config()
    if not check_r2_connection(config):
        print("ERROR: Cannot connect to R2 — fallback artwork not uploaded.")
        sys.exit(1)
    url = upload_fallback_artwork_to_r2(image_bytes, config)
    print(f"  Uploaded fallback artwork to R2: {url}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--asset", choices=[*ASSETS, "all"], default="all", help="Which asset to regenerate"
    )
    parser.add_argument(
        "--upload-fallback",
        action="store_true",
        help="Also upload the default episode art to R2 (the mid-pipeline fallback)",
    )
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    provider = OpenAIArtworkProvider(
        {
            "artwork": {
                "provider": "openai",
                "openai": {"model": "gpt-image-2"},
                "quality": "high",
                "timeout_seconds": 300,
            }
        }
    )
    print(f"Provider: {provider.name} (quality: {provider.quality})")

    names = list(ASSETS) if args.asset == "all" else [args.asset]
    default_bytes = None
    for name in names:
        image_bytes = generate_asset(provider, name)
        if name == "default":
            default_bytes = image_bytes

    if args.upload_fallback:
        if default_bytes is None:
            print("\n--upload-fallback given without regenerating 'default'; skipping upload.")
        else:
            print("\n=== Uploading fallback artwork to R2 ===")
            upload_fallback(default_bytes)

    print("\nDone. Review the images, then commit docs/ changes.")


if __name__ == "__main__":
    main()
