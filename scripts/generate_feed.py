#!/usr/bin/env python3
"""Generate RSS feed from episode JSON metadata.

This reads from podcast/episodes/*.json (single source of truth)
and generates docs/feed.xml.

Fast, reliable, no parsing or R2 calls needed.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent dir to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

import yaml
from podcast.episode_store import load_all_episodes
from podcast.rss_feed import create_episode_metadata, create_feed_xml, save_feed


def load_config():
    """Load configuration from config.yaml with environment overrides."""
    config_path = SCRIPT_DIR.parent / "podcast" / "config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Apply environment variable overrides
    for key in ["AUTHOR", "SITE_URL", "FEED_URL", "OWNER_EMAIL", "ARTWORK_URL", "AUTHOR_URL"]:
        env_var = f"VIBECAST_{key}"
        if os.environ.get(env_var):
            config_key = key.lower()
            config["podcast"][config_key] = os.environ[env_var]
    
    if os.environ.get("VIBECAST_R2_PUBLIC_URL"):
        config["storage"]["r2"]["public_base_url"] = os.environ["VIBECAST_R2_PUBLIC_URL"]
    
    return config


def episode_json_to_rss_metadata(episode: dict, config: dict) -> dict:
    """Convert episode JSON to RSS feed metadata format.
    
    Args:
        episode: Episode metadata from JSON
        config: Podcast configuration
    
    Returns:
        Episode metadata in RSS format (for create_episode_metadata)
    """
    # Convert stories from JSON format to ContentItem-like format
    items = []
    for story in episode.get("stories", []):
        item = type('ContentItem', (), story)()
        items.append(item)
    
    # Convert reading list
    reading_items = []
    for reading in episode.get("reading_list", []):
        item = type('ReadingItem', (), reading)()
        reading_items.append(item)
    
    # Parse date
    date = datetime.fromisoformat(episode["date"].replace('Z', '+00:00'))
    
    # Build metadata using existing function
    metadata = create_episode_metadata(
        date=date,
        mp3_url=episode["media"]["audio_url"],
        mp3_size=episode["media"]["audio_size_bytes"],
        duration_seconds=episode.get("duration_seconds"),
        config=config,
        items=items,
        episode_image_url=episode["media"].get("artwork_url"),
        custom_title=episode.get("title"),
        reading_items=reading_items,
        newspaper_url=episode["media"].get("newspaper_url"),
    )
    
    return metadata


def main():
    """Main entry point."""
    print("=" * 70)
    print("GENERATE RSS FEED FROM EPISODE METADATA")
    print("=" * 70)
    print()
    
    # Load config
    print("Loading configuration...")
    config = load_config()
    
    # Load episodes from JSON
    print("Loading episode metadata from JSON files...")
    episodes_json = load_all_episodes()
    
    if not episodes_json:
        print("✗ No episodes found in podcast/episodes/")
        return 1
    
    print(f"Found {len(episodes_json)} episodes")
    
    # Convert to RSS metadata format
    print("\nConverting to RSS format...")
    episodes_rss = []
    for episode in episodes_json:
        try:
            metadata = episode_json_to_rss_metadata(episode, config)
            episodes_rss.append(metadata)
        except Exception as e:
            print(f"  ✗ {episode['guid']}: {e}")
    
    print(f"Converted {len(episodes_rss)} episodes")
    
    # Generate RSS feed
    print("\nGenerating RSS XML...")
    feed_xml = create_feed_xml(config, episodes_rss)
    
    # Save feed
    feed_path = SCRIPT_DIR.parent / "docs" / "feed.xml"
    save_feed(str(feed_path), feed_xml)
    
    print(f"✓ Saved RSS feed to: {feed_path}")
    
    print("\n" + "=" * 70)
    print(f"COMPLETE: Generated feed with {len(episodes_rss)} episodes")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
