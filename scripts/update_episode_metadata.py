#!/usr/bin/env python3
"""Update all episode JSON files with complete metadata from R2 storage.

This script:
1. Reads existing episode JSON files
2. Updates them with current R2 metadata (URLs, file sizes)
3. Preserves existing data like stories and reading lists
4. Adds missing fields like newspaper_url and artwork_url
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent dir to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

import yaml

from podcast.storage import get_r2_client


def load_config():
    """Load configuration from config.yaml with environment overrides."""
    config_path = SCRIPT_DIR.parent / "podcast" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Apply environment variable overrides
    if os.environ.get("VIBECAST_R2_PUBLIC_URL"):
        config["storage"]["r2"]["public_base_url"] = os.environ["VIBECAST_R2_PUBLIC_URL"]

    return config


def update_episode_metadata(
    episode_id: str, config: dict, client, bucket: str, public_base_url: str
) -> dict:
    """Update episode metadata with current R2 info.

    Returns updated episode metadata dict or None if failed.
    """
    # Load existing JSON
    episodes_dir = SCRIPT_DIR.parent / "podcast" / "episodes"
    json_path = episodes_dir / f"{episode_id}.json"

    if not json_path.exists():
        print(f"  ✗ {episode_id}: JSON file not found")
        return None

    with open(json_path, encoding="utf-8") as f:
        episode_data = json.load(f)

    # Update media URLs from R2
    updated = False
    media = episode_data.get("media", {})

    # Update MP3
    mp3_key = f"episodes/{episode_id}.mp3"
    try:
        mp3_obj = client.head_object(Bucket=bucket, Key=mp3_key)
        mp3_size = mp3_obj["ContentLength"]
        mp3_url = f"{public_base_url.rstrip('/')}/{mp3_key}"

        if media.get("audio_url") != mp3_url or media.get("audio_size_bytes") != mp3_size:
            media["audio_url"] = mp3_url
            media["audio_size_bytes"] = mp3_size
            updated = True
    except Exception as e:
        print(f"  ⚠️  {episode_id}: Could not find MP3: {e}")

    # Update artwork
    artwork_key = f"episodes/{episode_id}/episode-art.png"
    try:
        client.head_object(Bucket=bucket, Key=artwork_key)
        artwork_url = f"{public_base_url.rstrip('/')}/{artwork_key}"
        if media.get("artwork_url") != artwork_url:
            media["artwork_url"] = artwork_url
            updated = True
    except:
        # No artwork found
        if "artwork_url" not in media or media["artwork_url"]:
            media["artwork_url"] = None

    # Update newspaper
    newspaper_key = f"episodes/{episode_id}/newspaper.pdf"
    try:
        client.head_object(Bucket=bucket, Key=newspaper_key)
        newspaper_url = f"{public_base_url.rstrip('/')}/{newspaper_key}"
        if media.get("newspaper_url") != newspaper_url:
            media["newspaper_url"] = newspaper_url
            updated = True
    except:
        # No newspaper found
        if "newspaper_url" not in media or media["newspaper_url"]:
            media["newspaper_url"] = None

    # Update transcript URL
    transcript_key = f"transcripts/{episode_id}.txt"
    transcript_url = f"{public_base_url.rstrip('/')}/{transcript_key}"
    if media.get("transcript_url") != transcript_url:
        media["transcript_url"] = transcript_url
        updated = True

    episode_data["media"] = media

    # Update metadata timestamp if anything changed
    if updated:
        if "metadata" not in episode_data:
            episode_data["metadata"] = {}
        episode_data["metadata"]["updated_at"] = datetime.now().isoformat()
        episode_data["metadata"]["updated_source"] = "update_episode_metadata"
        return episode_data
    else:
        return False  # Return False for unchanged, None for errors


def main():
    """Main entry point."""
    print("=" * 70)
    print("UPDATE EPISODE JSON METADATA FROM R2")
    print("=" * 70)
    print()
    print("This updates existing episode JSON files with current R2 URLs")
    print("and metadata (artwork, newspaper, audio, transcripts).")
    print()

    # Load config
    print("Loading configuration...")
    config = load_config()

    storage_config = config.get("storage", {})
    r2_config = storage_config.get("r2", {})

    bucket = r2_config.get("bucket", "vibecast")
    public_base_url = r2_config.get("public_base_url", "")

    if not public_base_url:
        print("✗ Error: VIBECAST_R2_PUBLIC_URL not set")
        return 1

    # Get existing episode JSON files
    episodes_dir = SCRIPT_DIR.parent / "podcast" / "episodes"
    if not episodes_dir.exists():
        print(f"✗ Episodes directory not found: {episodes_dir}")
        return 1

    json_files = sorted(episodes_dir.glob("*.json"))
    json_files = [f for f in json_files if f.name != ".gitkeep"]

    if not json_files:
        print("✗ No episode JSON files found")
        return 1

    print(f"Found {len(json_files)} episode JSON files\n")

    # Connect to R2
    print("Connecting to R2 storage...")
    client = get_r2_client()

    # Update each episode
    print("Updating episode metadata...\n")
    updated_count = 0
    unchanged_count = 0
    failed_count = 0

    for json_file in json_files:
        episode_id = json_file.stem

        updated_data = update_episode_metadata(episode_id, config, client, bucket, public_base_url)

        if updated_data is None:
            # Error occurred
            failed_count += 1
        elif updated_data is False:
            # No changes needed
            print(f"  ⏭️  {episode_id}: No changes needed")
            unchanged_count += 1
        else:
            # Save updated JSON
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(updated_data, f, indent=2, ensure_ascii=False)

            media = updated_data.get("media", {})
            has_artwork = "✓ art" if media.get("artwork_url") else "✗ art"
            has_newspaper = "✓ pdf" if media.get("newspaper_url") else "✗ pdf"
            print(f"  ✓ {episode_id}: Updated ({has_artwork}, {has_newspaper})")
            updated_count += 1

    print(f"\n{'=' * 70}")
    print("COMPLETE:")
    print(f"  - Updated: {updated_count}")
    print(f"  - Unchanged: {unchanged_count}")
    print(f"  - Failed: {failed_count}")
    print(f"{'=' * 70}")

    if updated_count > 0:
        print("\nNext steps:")
        print("  1. Review updated JSON files")
        print("  2. Run: python scripts/regenerate_all.py")
        print("  3. Commit and push changes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
