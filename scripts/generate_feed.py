#!/usr/bin/env python3
"""Generate RSS feed from episode JSON metadata.

This reads from podcast/episodes/*.json (single source of truth)
and generates docs/feed.xml.

Fast, reliable, no parsing or R2 calls needed.
"""

import os
import sys
from pathlib import Path

# Add parent dir to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

import yaml

from podcast.episode_store import load_all_episodes
from podcast.rss_feed import generate_feed_from_store, save_feed


def load_config():
    """Load configuration from config.yaml with environment overrides."""
    config_path = SCRIPT_DIR.parent / "podcast" / "config.yaml"
    with open(config_path) as f:
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

    # Generate RSS feed from the episode store
    print("\nGenerating RSS XML...")
    feed_xml = generate_feed_from_store(config)

    # Save feed
    feed_path = SCRIPT_DIR.parent / "docs" / "feed.xml"
    save_feed(str(feed_path), feed_xml)

    print(f"✓ Saved RSS feed to: {feed_path}")

    print("\n" + "=" * 70)
    print(f"COMPLETE: Generated feed with {len(episodes_json)} episodes")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
