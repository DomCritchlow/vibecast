#!/usr/bin/env python3
"""Generate theme-sting candidates for special episodes with the Music API.

Writes N candidate stings to podcast/assets/theme-candidates/. Listen, pick
your favorite, and commit it as podcast/assets/theme.mp3 — the special
episode pipeline picks it up from there (missing file just means no sting).

Usage:
    ELEVENLABS_API_KEY=... uv run python scripts/generate_theme.py
    uv run python scripts/generate_theme.py --candidates 5 --seconds 12
    uv run python scripts/generate_theme.py --prompt "your own idea"

Cost: ~$0.15 per minute of music, so a batch of 3 x 12s stings is ~$0.09.
"""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
CANDIDATES_DIR = REPO_ROOT / "podcast" / "assets" / "theme-candidates"

# Matched to the show: curious, informed, engaged-but-chill morning energy.
DEFAULT_PROMPT = (
    "Short instrumental podcast intro sting: warm analog synth and soft keys, "
    "gentle upbeat morning energy, a hint of lo-fi texture, curious and optimistic, "
    "clean ending that can fade under a speaking voice. No vocals."
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--candidates", type=int, default=3, help="How many to generate")
    parser.add_argument("--seconds", type=float, default=12.0, help="Sting length in seconds")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Music prompt")
    parser.add_argument(
        "--provider",
        default="fal",
        choices=["fal", "elevenlabs"],
        help="Music transport (default: fal, no subscription)",
    )
    args = parser.parse_args()

    if args.provider == "fal":
        if not os.environ.get("FAL_KEY"):
            print("FAL_KEY is not set")
            return 1
        from podcast.tts.fal_tts import fal_music

        def compose(prompt, seconds):
            return fal_music(prompt, seconds, force_instrumental=True)
    else:
        if not os.environ.get("ELEVENLABS_API_KEY"):
            print("ELEVENLABS_API_KEY is not set")
            return 1
        from elevenlabs import ElevenLabs

        client = ElevenLabs()

        def compose(prompt, seconds):
            return b"".join(
                client.music.compose(
                    prompt=prompt,
                    music_length_ms=int(seconds * 1000),
                    force_instrumental=True,
                )
            )

    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Provider: {args.provider}\nPrompt: {args.prompt}\n")
    for i in range(1, args.candidates + 1):
        print(f"Composing candidate {i}/{args.candidates} ({args.seconds:.0f}s)...")
        try:
            audio = compose(args.prompt, args.seconds)
        except Exception as e:
            print(f"  FAILED: {e}")
            continue
        path = CANDIDATES_DIR / f"theme-{i:02d}.mp3"
        path.write_bytes(audio)
        print(f"  -> {path}")

    print(f"\nDone. Listen with: open {CANDIDATES_DIR}/*.mp3")
    print("Commit your pick as podcast/assets/theme.mp3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
