#!/usr/bin/env python3
"""Audition ElevenLabs voices for Bento before picking one in config.yaml.

Synthesizes the same sample paragraph (with Eleven v3 audio tags) across a
shortlist of narrator voices and writes one MP3 per voice to auditions/.
Listen, pick, then set tts.elevenlabs.voice_id in podcast/config.yaml.

Usage:
    ELEVENLABS_API_KEY=... uv run python scripts/audition_voices.py
    uv run python scripts/audition_voices.py --voices george brian lily
    uv run python scripts/audition_voices.py --voices <raw-voice-id>
    uv run python scripts/audition_voices.py --mine   # voices saved in your account

--mine pulls every voice saved in your ElevenLabs account ("My Voices"),
so you can shortlist candidates in the voice library on the website, then
hear them all read Bento here. Requires the Voices (read) permission on
the API key.

Cost: the sample is ~450 characters, so about $0.05 per voice on v3.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from podcast.tts.elevenlabs import get_voice_description

# The register we're casting for: curious, warm, a little wry — with the
# audio tags the daily prompt is allowed to use, so we hear them performed.
SAMPLE = """Hey, it's Bento. Here's one that stopped me mid-coffee this morning. \
[curious] A team in Zurich taught a swarm of paper-airplane drones to ride thermal \
updrafts — no motors, just physics and patience. [chuckles] The lead researcher \
says they got the idea watching hawks circle over a parking lot. \
And look — it's a gorgeous, clear morning here in New York. [warmly] Sixty-eight \
degrees, the kind of day that makes the news feel lighter than it is. \
That's the thread. Go make something happen."""

DEFAULT_SHORTLIST = ["george", "daniel", "brian", "will", "callum", "lily"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--voices",
        nargs="+",
        default=None,
        help=f"Preset names or raw voice IDs (default: {' '.join(DEFAULT_SHORTLIST)})",
    )
    parser.add_argument(
        "--mine",
        action="store_true",
        help="Audition every voice saved in your ElevenLabs account instead",
    )
    parser.add_argument("--model", default="eleven_v3", help="Model ID (default: eleven_v3)")
    parser.add_argument(
        "--provider",
        default="fal",
        choices=["fal", "elevenlabs"],
        help="Transport to audition on (default: fal, the shipping transport)",
    )
    parser.add_argument("--out", default="auditions", help="Output directory")
    args = parser.parse_args()

    from podcast.tts import get_tts_provider

    if args.provider == "fal" and not os.environ.get("FAL_KEY"):
        print("FAL_KEY is not set")
        return 1
    if args.provider == "elevenlabs" and not os.environ.get("ELEVENLABS_API_KEY"):
        print("ELEVENLABS_API_KEY is not set")
        return 1

    if args.mine:
        voices = list_account_voices()
        if not voices:
            print("No voices found in your account — save some from elevenlabs.io/voice-library")
            return 1
    else:
        voices = [(v, v) for v in (args.voices or DEFAULT_SHORTLIST)]

    out_dir = Path(args.out)
    out_dir.mkdir(exist_ok=True)

    for label, voice_ref in voices:
        # Both providers read the voice from tts.elevenlabs.voice_id; fal
        # resolves it to its voice-name form.
        config = {
            "tts": {
                "provider": args.provider,
                "elevenlabs": {
                    "voice_id": voice_ref,
                    "model_id": args.model,
                    "format": "mp3_44100_128",
                },
                "fal": {"format": "mp3_44100_128"},
            }
        }
        provider = get_tts_provider(config)
        description = get_voice_description(label)
        print(f"Synthesizing {label}" + (f" ({description})" if description else "") + "...")
        try:
            audio = provider.synthesize(SAMPLE)
        except Exception as e:
            print(f"  FAILED: {e}")
            continue
        path = out_dir / f"{label}.mp3"
        path.write_bytes(audio)
        print(f"  -> {path}")

    print(f"\nDone. Listen with: open {out_dir}/*.mp3")
    print("Then set tts.elevenlabs.voice_id in podcast/config.yaml")
    return 0


def list_account_voices() -> list[tuple[str, str]]:
    """(name, voice_id) for every voice saved in the ElevenLabs account."""
    from elevenlabs import ElevenLabs

    response = ElevenLabs().voices.get_all()
    voices = []
    for v in response.voices:
        name = (v.name or v.voice_id).lower().replace(" ", "-")
        category = getattr(v, "category", "") or ""
        print(f"  found: {name:24s} {v.voice_id}  [{category}]")
        voices.append((name, v.voice_id))
    return voices


if __name__ == "__main__":
    sys.exit(main())
