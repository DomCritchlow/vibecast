#!/usr/bin/env python3
"""Migrate existing episodes to JSON metadata format.

This script:
1. Scans R2 storage for all episodes
2. Fetches transcripts to extract story references
3. Creates podcast/episodes/{date}.json files with all metadata
4. This becomes the single source of truth for all episode data
"""

import sys
import os
import re
import json
from pathlib import Path
from datetime import datetime

# Add parent dir to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from podcast.storage import get_r2_client
from podcast.sources.base import ContentItem
import yaml


def load_config():
    """Load configuration from config.yaml with environment overrides."""
    config_path = SCRIPT_DIR.parent / "podcast" / "config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Apply environment variable overrides
    if os.environ.get("VIBECAST_R2_PUBLIC_URL"):
        config["storage"]["r2"]["public_base_url"] = os.environ["VIBECAST_R2_PUBLIC_URL"]
    
    return config


def extract_metadata_from_transcript(transcript_text: str) -> dict:
    """Extract all metadata from transcript.
    
    Returns dict with:
        - duration_seconds: float
        - stories: list of dicts
        - reading_list: list of dicts
        - custom_title: str or None
    """
    metadata = {
        "duration_seconds": None,
        "stories": [],
        "reading_list": [],
        "custom_title": None
    }
    
    # Extract duration
    duration_match = re.search(r"Duration: ~(\d+\.?\d*) minutes", transcript_text)
    if duration_match:
        metadata["duration_seconds"] = float(duration_match.group(1)) * 60
    
    # Extract custom title (if not default "Morning Thread")
    title_match = re.search(r"^VIBECAST TRANSCRIPT\n(.+?) — ", transcript_text, re.MULTILINE)
    if title_match:
        potential_title = title_match.group(1)
        if potential_title != "Morning Thread":
            metadata["custom_title"] = potential_title
    
    # Extract REFERENCES section
    references_match = re.search(
        r'REFERENCES\n-+\n(.+?)(?=\n\nREADING LIST|\n\nPROMPTS USED|$)',
        transcript_text,
        re.DOTALL
    )
    
    if references_match:
        references_text = references_match.group(1)
        entries = re.findall(
            r'(\d+)\.\s+(.+?)\n\s+Source:\s+(.+?)\n\s+Link:\s+(.+?)(?=\n\n|\n\d+\.|\Z)',
            references_text,
            re.DOTALL
        )
        
        for num, title, source, url in entries:
            metadata["stories"].append({
                "title": title.strip(),
                "source": source.strip(),
                "url": url.strip(),
                "summary": ""  # Summaries not in transcripts
            })
    
    # Extract READING LIST section
    reading_match = re.search(
        r'READING LIST\n-+\n(.+?)(?=\n\nPROMPTS USED|$)',
        transcript_text,
        re.DOTALL
    )
    
    if reading_match:
        reading_text = reading_match.group(1)
        entries = re.findall(
            r'(\d+)\.\s+(.+?)\n\s+Source:\s+(.+?)\n\s+Link:\s+(.+?)(?=\n\n|\n\d+\.|\Z)',
            reading_text,
            re.DOTALL
        )
        
        for num, title_line, source, url in entries:
            title_line = title_line.strip()
            source = source.strip()
            url = url.strip()
            
            # Extract author if present
            author = ""
            if " by " in title_line:
                title, author = title_line.rsplit(" by ", 1)
            else:
                title = title_line
            
            metadata["reading_list"].append({
                "title": title,
                "author": author,
                "source": source,
                "url": url,
                "description": ""
            })
    
    return metadata


def migrate_episode_to_json(episode_id: str, config: dict, client, bucket: str, public_base_url: str) -> dict:
    """Migrate a single episode to JSON format.
    
    Returns episode metadata dict or None if failed.
    """
    try:
        # Parse date
        date = datetime.strptime(episode_id, "%Y-%m-%d")
    except ValueError:
        print(f"  ✗ {episode_id}: Invalid date format")
        return None
    
    # Get MP3 info
    mp3_key = f"episodes/{episode_id}.mp3"
    try:
        mp3_obj = client.head_object(Bucket=bucket, Key=mp3_key)
        mp3_size = mp3_obj["ContentLength"]
        mp3_url = f"{public_base_url.rstrip('/')}/{mp3_key}"
    except:
        print(f"  ✗ {episode_id}: MP3 not found")
        return None
    
    # Check for artwork
    artwork_key = f"episodes/{episode_id}/episode-art.png"
    artwork_url = None
    try:
        client.head_object(Bucket=bucket, Key=artwork_key)
        artwork_url = f"{public_base_url.rstrip('/')}/{artwork_key}"
    except:
        pass
    
    # Check for newspaper
    newspaper_url = None
    newspaper_key = f"newspapers/{episode_id}.pdf"
    try:
        client.head_object(Bucket=bucket, Key=newspaper_key)
        newspaper_url = f"{public_base_url.rstrip('/')}/{newspaper_key}"
    except:
        pass
    
    # Get transcript and extract metadata
    transcript_key = f"transcripts/{episode_id}.txt"
    transcript_metadata = {
        "duration_seconds": (mp3_size / 1_000_000) * 60,  # Estimate
        "stories": [],
        "reading_list": [],
        "custom_title": None
    }
    
    try:
        transcript_obj = client.get_object(Bucket=bucket, Key=transcript_key)
        transcript_text = transcript_obj["Body"].read().decode("utf-8")
        transcript_metadata = extract_metadata_from_transcript(transcript_text)
    except Exception as e:
        print(f"  ⚠️  {episode_id}: Could not parse transcript: {e}")
    
    # Build episode metadata
    podcast = config.get("podcast", {})
    
    # Determine title
    if transcript_metadata["custom_title"]:
        title = transcript_metadata["custom_title"]
    else:
        # Use default format
        vibe = config.get("vibe", {})
        vibe_name = vibe.get("name", podcast.get("title", "Vibecast"))
        date_formatted = date.strftime("%B %d, %Y")
        title = f"{vibe_name} — {date_formatted}"
    
    # Format duration
    duration_seconds = transcript_metadata["duration_seconds"]
    if duration_seconds:
        hours, remainder = divmod(int(duration_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            duration_formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            duration_formatted = f"{minutes}:{seconds:02d}"
    else:
        duration_formatted = "0:00"
    
    episode_data = {
        "guid": episode_id,
        "date": date.isoformat(),
        "title": title,
        "tagline": podcast.get("tagline", "Your daily podcast"),
        "duration_seconds": duration_seconds,
        "duration_formatted": duration_formatted,
        
        "media": {
            "audio_url": mp3_url,
            "audio_size_bytes": mp3_size,
            "artwork_url": artwork_url,
            "newspaper_url": newspaper_url,
            "transcript_url": f"{public_base_url.rstrip('/')}/{transcript_key}"
        },
        
        "stories": transcript_metadata["stories"],
        "reading_list": transcript_metadata["reading_list"],
        
        "metadata": {
            "migrated_at": datetime.now().isoformat(),
            "migration_source": "r2_storage"
        }
    }
    
    return episode_data


def main():
    """Main entry point."""
    print("=" * 70)
    print("MIGRATE EPISODES TO JSON METADATA")
    print("=" * 70)
    print()
    print("This creates podcast/episodes/*.json files from R2 storage.")
    print("These JSON files become the single source of truth.")
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
    
    # Setup output directory
    episodes_dir = SCRIPT_DIR.parent / "podcast" / "episodes"
    episodes_dir.mkdir(parents=True, exist_ok=True)
    
    # Connect to R2
    print("\nConnecting to R2 storage...")
    client = get_r2_client()
    
    # List all MP3 files
    print("Scanning for episodes...")
    response = client.list_objects_v2(
        Bucket=bucket,
        Prefix="episodes/",
        MaxKeys=1000
    )
    
    episode_ids = []
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if not key.endswith(".mp3") or key.count("/") > 1:
            continue
        
        filename = key.split("/")[-1]
        episode_id = filename.replace(".mp3", "")
        
        if re.match(r"\d{4}-\d{2}-\d{2}", episode_id):
            episode_ids.append(episode_id)
    
    episode_ids.sort()
    print(f"Found {len(episode_ids)} episodes\n")
    
    # Migrate each episode
    print("Migrating episodes to JSON...")
    migrated = 0
    failed = 0
    
    for episode_id in episode_ids:
        # Check if already exists
        json_path = episodes_dir / f"{episode_id}.json"
        if json_path.exists():
            print(f"  ⏭️  {episode_id}: Already exists, skipping")
            continue
        
        # Migrate
        episode_data = migrate_episode_to_json(
            episode_id,
            config,
            client,
            bucket,
            public_base_url
        )
        
        if episode_data:
            # Save to JSON
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(episode_data, f, indent=2, ensure_ascii=False)
            
            story_count = len(episode_data["stories"])
            reading_count = len(episode_data["reading_list"])
            print(f"  ✓ {episode_id}: {story_count} stories, {reading_count} reading items")
            migrated += 1
        else:
            failed += 1
    
    print(f"\n{'=' * 70}")
    print(f"COMPLETE: Migrated {migrated} episodes, {failed} failed")
    print(f"{'=' * 70}")
    print(f"\nJSON files saved to: {episodes_dir}")
    print("\nNext steps:")
    print("  1. Review generated JSON files")
    print("  2. Run: python scripts/generate_feed.py")
    print("  3. Run: python scripts/generate_site.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
