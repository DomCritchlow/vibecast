#!/usr/bin/env python3
"""Regenerate AI titles for episodes that have boring default titles.

This script:
1. Loads all episodes from JSON
2. Identifies episodes with default/boring titles
3. Generates new AI titles based on their stories
4. Updates the JSON files
5. Regenerates the site
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent dir to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from podcast.episode_store import load_all_episodes, save_episode
from podcast.sources.base import ContentItem
from podcast.writer import generate_episode_title


def has_boring_title(title: str) -> bool:
    """Check if title is boring/generic."""
    boring_patterns = [
        "Morning Thread",
        "Daily Thread",
        "Vibecast",
        "Episode",
    ]

    # If title is just "Name — Date" format, it's boring
    if " — " in title and any(pattern in title for pattern in boring_patterns):
        return True

    # If title contains date but no interesting content
    if any(
        month in title
        for month in [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
    ):
        if not any(c.isdigit() and c != "2" for c in title.replace(",", "").replace(" ", "")):
            return True

    return False


def generate_title_from_stories(
    stories: list, config: dict, vibe_name: str = "Morning Thread"
) -> str:
    """Generate an AI title from episode stories."""
    if not stories:
        return f"{vibe_name} Episode"

    # Convert to ContentItem objects
    items = []
    for story in stories[:6]:  # Use up to 6 stories
        item = ContentItem(
            title=story["title"],
            url=story["url"],
            summary=story.get("summary", ""),
            source=story["source"],
        )
        items.append(item)

    # Generate title using AI
    try:
        title = generate_episode_title(items, config)
        print(f"      Generated: {title}")
        return title
    except Exception as e:
        print(f"      Error generating title: {e}")
        return None


def load_config():
    """Load configuration from config.yaml with environment overrides."""
    config_path = SCRIPT_DIR.parent / "podcast" / "config.yaml"
    import yaml

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
    print("REGENERATE EPISODE TITLES")
    print("=" * 70)
    print()
    print("This script regenerates AI titles for episodes with boring titles.")
    print()

    # Load config
    print("Loading configuration...")
    config = load_config()

    # Load all episodes
    print("Loading episodes...")
    episodes = load_all_episodes(reverse=False)  # Oldest first
    print(f"Found {len(episodes)} episodes")
    print()

    # Find episodes with boring titles
    boring_episodes = []
    for ep in episodes:
        if has_boring_title(ep["title"]):
            boring_episodes.append(ep)

    if not boring_episodes:
        print("✓ All episodes have interesting titles!")
        return 0

    print(f"Found {len(boring_episodes)} episodes with boring titles")
    print()

    # Ask for confirmation
    print("This will use OpenAI API to generate new titles.")
    print(f"Estimated cost: ~${len(boring_episodes) * 0.01:.2f} (rough estimate)")
    print()
    response = input(f"Regenerate titles for {len(boring_episodes)} episodes? (y/N): ")

    if response.lower() != "y":
        print("Cancelled.")
        return 0

    print()
    print("Regenerating titles...")
    print()

    # Regenerate titles
    updated = 0
    skipped = 0
    failed = 0

    for ep in boring_episodes:
        episode_id = ep["guid"]
        old_title = ep["title"]

        print(f"  {episode_id}")
        print(f"    Old: {old_title}")

        # Generate new title
        new_title = generate_title_from_stories(ep["stories"], config=config)

        if new_title and new_title != old_title:
            # Update episode
            ep["title"] = new_title
            ep["metadata"]["title_regenerated_at"] = datetime.now().isoformat()

            # Save
            save_episode(ep)
            print("    ✓ Updated")
            updated += 1
        elif not new_title:
            print("    ✗ Failed to generate")
            failed += 1
        else:
            print("    ⏭️  Same title, skipping")
            skipped += 1

        print()

    print("=" * 70)
    print(f"COMPLETE: Updated {updated}, skipped {skipped}, failed {failed}")
    print("=" * 70)
    print()

    if updated > 0:
        print("Next steps:")
        print("  1. Review updated titles in podcast/episodes/")
        print("  2. Run: python scripts/regenerate_all.py")
        print("  3. Commit: git add podcast/episodes/ docs/")
        print("  4. Push: git push")

    return 0


if __name__ == "__main__":
    sys.exit(main())
