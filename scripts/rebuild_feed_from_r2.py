#!/usr/bin/env python3
"""Rebuild RSS feed from episodes in R2 storage.

This is safe to run - it preserves episode GUIDs and dates so podcast players
won't see existing episodes as "new". Use this when you need to update the
feed structure/format without creating new content.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import re

# Add parent dir to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from podcast.storage import get_r2_client
from podcast.rss_feed import create_episode_metadata, create_feed_xml, save_feed
import yaml


def load_config():
    """Load configuration from config.yaml."""
    config_path = SCRIPT_DIR.parent / "podcast" / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_episodes_from_r2(config: dict) -> list[dict]:
    """Scan R2 for all episodes and build metadata.
    
    Preserves episode identity (GUID, date) so podcast players don't see
    them as new episodes.
    
    Returns:
        List of episode metadata dictionaries, sorted by date (newest first).
    """
    storage_config = config.get("storage", {})
    r2_config = storage_config.get("r2", {})
    
    bucket = r2_config.get("bucket", "vibecast")
    public_base_url = r2_config.get("public_base_url", "")
    
    client = get_r2_client()
    
    # List all MP3 files in episodes/
    response = client.list_objects_v2(
        Bucket=bucket,
        Prefix="episodes/",
        MaxKeys=1000
    )
    
    episodes = []
    
    for obj in response.get("Contents", []):
        key = obj["Key"]
        
        # Only process .mp3 files in the episodes/ root (not in subdirectories)
        if not key.endswith(".mp3") or key.count("/") > 1:
            continue
        
        # Extract date from filename: episodes/2026-01-21.mp3 -> 2026-01-21
        filename = key.split("/")[-1]
        episode_id = filename.replace(".mp3", "")
        
        # Validate date format
        if not re.match(r"\d{4}-\d{2}-\d{2}", episode_id):
            print(f"  Skipping invalid filename: {filename}")
            continue
        
        # Parse date
        try:
            date = datetime.strptime(episode_id, "%Y-%m-%d")
        except ValueError:
            print(f"  Skipping invalid date: {episode_id}")
            continue
        
        # Build MP3 URL
        if public_base_url:
            mp3_url = f"{public_base_url.rstrip('/')}/{key}"
        else:
            account_id = os.environ.get("R2_ACCOUNT_ID", "")
            mp3_url = f"https://{bucket}.{account_id}.r2.dev/{key}"
        
        mp3_size = obj["Size"]
        
        # Check for artwork
        artwork_key = f"episodes/{episode_id}/episode-art.png"
        artwork_url = None
        try:
            client.head_object(Bucket=bucket, Key=artwork_key)
            if public_base_url:
                artwork_url = f"{public_base_url.rstrip('/')}/{artwork_key}"
            else:
                account_id = os.environ.get("R2_ACCOUNT_ID", "")
                artwork_url = f"https://{bucket}.{account_id}.r2.dev/{artwork_key}"
        except:
            pass
        
        # Try to get duration and title from transcript
        transcript_key = f"transcripts/{episode_id}.txt"
        duration_seconds = None
        
        try:
            transcript_obj = client.get_object(Bucket=bucket, Key=transcript_key)
            transcript_text = transcript_obj["Body"].read().decode("utf-8")
            
            # Extract duration from transcript
            duration_match = re.search(r"Duration: ~(\d+\.?\d*) minutes", transcript_text)
            if duration_match:
                duration_seconds = float(duration_match.group(1)) * 60
        except:
            # If no transcript, estimate from MP3 size (very rough: ~1MB per minute)
            duration_seconds = (mp3_size / 1_000_000) * 60
        
        # Create episode metadata (GUID = date, so it's stable)
        episode = create_episode_metadata(
            date=date,
            mp3_url=mp3_url,
            mp3_size=mp3_size,
            duration_seconds=duration_seconds,
            config=config,
            items=[],  # We don't have the original items, but that's okay
            episode_image_url=artwork_url,
            custom_title=None,  # Will use default format
        )
        
        episodes.append(episode)
        artwork_status = "✓" if artwork_url else "✗"
        print(f"  {episode_id}: {mp3_size:>10,} bytes | artwork: {artwork_status}")
    
    # Sort by date (newest first)
    episodes.sort(key=lambda e: e["pub_date"], reverse=True)
    
    return episodes


def main():
    """Main entry point."""
    print("=" * 70)
    print("REBUILD RSS FEED FROM R2 STORAGE")
    print("=" * 70)
    print()
    print("This rebuilds the RSS feed from existing episodes in R2.")
    print("Episode GUIDs and dates are preserved, so podcast players won't")
    print("see existing episodes as 'new'. Safe for structure/format updates.")
    print()
    
    # Load config
    print("Loading configuration...")
    config = load_config()
    
    # Scan R2 for episodes
    print("\nScanning R2 storage for episodes...")
    episodes = get_episodes_from_r2(config)
    
    if not episodes:
        print("\n✗ No episodes found in R2")
        return 1
    
    print(f"\nFound {len(episodes)} episodes")
    
    # Generate RSS feed
    print("\nGenerating RSS feed...")
    feed_xml = create_feed_xml(config, episodes)
    
    # Save feed
    feed_path = SCRIPT_DIR.parent / "docs" / "feed.xml"
    save_feed(str(feed_path), feed_xml)
    
    print(f"✓ Saved feed to: {feed_path}")
    
    print("\n" + "=" * 70)
    print(f"COMPLETE: Rebuilt feed with {len(episodes)} episodes")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
