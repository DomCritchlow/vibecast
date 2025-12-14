#!/usr/bin/env python3
"""Main orchestrator for Vibecast daily podcast generation."""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from .sources.base import filter_items, select_items, ContentItem
from .sources.weather import fetch_weather, format_weather_for_script
from .sources.rss import fetch_all_rss_sources
from .sources.nasa_apod import get_apod_for_episode
from .writer import generate_script, generate_script_dry_run
from .tts import synthesize_mp3, estimate_audio_duration
from .storage import upload_mp3_to_r2, upload_transcript_to_r2, check_r2_connection
from .rss_feed import create_episode_metadata, update_feed, save_feed
from .site_generator import save_index_html


# Paths relative to this file
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
STATE_PATH = SCRIPT_DIR / "state.json"
SITE_DIR = SCRIPT_DIR.parent / "site"
FEED_PATH = SITE_DIR / "feed.xml"
SCRIPTS_DIR = SITE_DIR / "scripts"


def load_config() -> dict:
    """Load configuration from config.yaml with environment variable overrides."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
    
    # Apply environment variable overrides for personal settings
    config = _apply_env_overrides(config)
    
    return config


def _apply_env_overrides(config: dict) -> dict:
    """Apply environment variable overrides to config.
    
    This allows personal settings to be kept out of the committed config.yaml
    while still having sensible defaults for others who clone the repo.
    """
    # Location overrides
    if os.environ.get("VIBECAST_LOCATION_NAME"):
        config["location"]["name"] = os.environ["VIBECAST_LOCATION_NAME"]
    if os.environ.get("VIBECAST_LOCATION_LAT"):
        config["location"]["lat"] = float(os.environ["VIBECAST_LOCATION_LAT"])
    if os.environ.get("VIBECAST_LOCATION_LON"):
        config["location"]["lon"] = float(os.environ["VIBECAST_LOCATION_LON"])
    
    # Podcast identity overrides
    if os.environ.get("VIBECAST_AUTHOR"):
        config["podcast"]["author"] = os.environ["VIBECAST_AUTHOR"]
    if os.environ.get("VIBECAST_SITE_URL"):
        config["podcast"]["site_url"] = os.environ["VIBECAST_SITE_URL"]
    if os.environ.get("VIBECAST_FEED_URL"):
        config["podcast"]["feed_url"] = os.environ["VIBECAST_FEED_URL"]
    if os.environ.get("VIBECAST_OWNER_EMAIL"):
        config["podcast"]["owner_email"] = os.environ["VIBECAST_OWNER_EMAIL"]
    if os.environ.get("VIBECAST_ARTWORK_URL"):
        config["podcast"]["artwork_url"] = os.environ["VIBECAST_ARTWORK_URL"]
    if os.environ.get("VIBECAST_AUTHOR_URL"):
        config["podcast"]["author_url"] = os.environ["VIBECAST_AUTHOR_URL"]
    
    # Storage overrides
    if os.environ.get("VIBECAST_R2_PUBLIC_URL"):
        config["storage"]["r2"]["public_base_url"] = os.environ["VIBECAST_R2_PUBLIC_URL"]
    
    # Schedule overrides
    if os.environ.get("VIBECAST_TIMEZONE"):
        config["schedule"]["timezone"] = os.environ["VIBECAST_TIMEZONE"]
    
    return config


def load_state() -> dict:
    """Load state from state.json (used URLs for deduplication)."""
    if not STATE_PATH.exists():
        return {"used_urls": [], "last_run": None}
    
    try:
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"used_urls": [], "last_run": None}


def save_state(state: dict) -> None:
    """Save state to state.json."""
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def save_transcript(
    date: datetime,
    script_result: dict,
    items: list[ContentItem],
    config: dict,
    estimated_duration: float,
) -> Path:
    """Save the episode transcript with prompts, script, and references.
    
    Args:
        date: Episode date.
        script_result: Dict with 'script', 'system_prompt', 'user_prompt', 'model'.
        items: Content items used in the episode.
        config: Full configuration dictionary.
        estimated_duration: Estimated duration in minutes.
    
    Returns:
        Path to the saved transcript file.
    """
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    
    filename = f"{date.strftime('%Y-%m-%d')}.txt"
    filepath = SCRIPTS_DIR / filename
    
    # Extract script result
    script = script_result.get("script", "")
    system_prompt = script_result.get("system_prompt", "")
    user_prompt = script_result.get("user_prompt", "")
    model = script_result.get("model", "unknown")
    
    # Get podcast info
    podcast = config.get("podcast", {})
    vibe = config.get("vibe", {})
    
    # Build the transcript document
    lines = [
        "=" * 70,
        f"VIBECAST TRANSCRIPT",
        f"{vibe.get('name', 'Episode')} — {date.strftime('%A, %B %d, %Y')}",
        "=" * 70,
        "",
        "EPISODE SUMMARY",
        "-" * 40,
        f"Date: {date.strftime('%Y-%m-%d')}",
        f"Duration: ~{estimated_duration:.1f} minutes",
        f"Model: {model}",
        f"Stories covered: {len(items)}",
        "",
        "Sources featured in this episode:",
    ]
    
    # List sources
    sources_seen = set()
    for item in items:
        if item.source not in sources_seen:
            lines.append(f"  • {item.source}")
            sources_seen.add(item.source)
    
    lines.extend([
        "",
        "",
        "FULL SCRIPT",
        "-" * 40,
        "",
        script,
        "",
        "",
        "REFERENCES",
        "-" * 40,
        "Links to the stories mentioned in this episode:",
        "",
    ])
    
    # Add references with full details
    for i, item in enumerate(items, 1):
        lines.extend([
            f"{i}. {item.title}",
            f"   Source: {item.source}",
            f"   Link: {item.url}",
            "",
        ])
    
    lines.extend([
        "",
        "",
        "PROMPTS USED",
        "=" * 70,
        "",
        "SYSTEM PROMPT",
        "-" * 40,
        "",
        system_prompt,
        "",
        "",
        "USER PROMPT",
        "-" * 40,
        "",
        user_prompt,
        "",
        "",
        "-" * 70,
        f"Generated by Vibecast • {podcast.get('site_url', '')}",
        "-" * 70,
    ])
    
    # Write the file
    content = "\n".join(lines)
    filepath.write_text(content, encoding="utf-8")
    
    return filepath


def clean_old_urls(state: dict, dedupe_days: int) -> dict:
    """Remove URLs older than dedupe_days from state."""
    cutoff = datetime.now() - timedelta(days=dedupe_days)
    cutoff_str = cutoff.isoformat()
    
    # Filter URLs that have timestamps newer than cutoff
    if "url_timestamps" in state:
        state["url_timestamps"] = {
            url: ts for url, ts in state["url_timestamps"].items()
            if ts > cutoff_str
        }
        state["used_urls"] = list(state["url_timestamps"].keys())
    
    return state


def run_pipeline(dry_run: bool = False, verbose: bool = False) -> bool:
    """Run the complete podcast generation pipeline.
    
    Args:
        dry_run: If True, skip TTS and upload steps.
        verbose: If True, print detailed progress.
    
    Returns:
        True if successful, False otherwise.
    """
    print("=" * 60)
    print("VIBECAST - Daily Podcast Generator")
    print("=" * 60)
    
    if dry_run:
        print("\n[DRY RUN MODE - No API calls or uploads will be made]\n")
    
    try:
        # 1. Load configuration
        print("\n[1/8] Loading configuration...")
        config = load_config()
        print(f"  Vibe: {config.get('vibe', {}).get('name', 'Unknown')}")
        print(f"  Podcast: {config.get('podcast', {}).get('title', 'Unknown')}")
        
        # 2. Load and clean state
        print("\n[2/8] Loading state...")
        state = load_state()
        dedupe_days = config.get("filters", {}).get("dedupe_days", 7)
        state = clean_old_urls(state, dedupe_days)
        used_urls = set(state.get("used_urls", []))
        print(f"  Tracking {len(used_urls)} recently used URLs")
        
        # 3. Fetch weather
        print("\n[3/8] Fetching weather...")
        location = config.get("location", {})
        lat = location.get("lat", 0.0)
        lon = location.get("lon", 0.0)
        
        if lat == 0.0 and lon == 0.0:
            print("  Warning: Location not configured, skipping weather")
            weather_text = "Weather information is not available today."
        else:
            weather_config = config.get("sources", {}).get("weather", {})
            weather_data = fetch_weather(
                lat=lat,
                lon=lon,
                units=location.get("units", "fahrenheit"),
                include_forecast=weather_config.get("include_forecast", True),
                forecast_days=weather_config.get("forecast_days", 1),
            )
            
            if weather_data:
                weather_text = format_weather_for_script(weather_data, location.get("name", "your area"))
                print(f"  {weather_text[:80]}...")
            else:
                weather_text = f"Weather for {location.get('name', 'your area')} is currently unavailable."
                print("  Weather fetch failed, using fallback")
        
        # 4. Fetch RSS content
        print("\n[4/8] Fetching RSS feeds...")
        rss_sources = config.get("sources", {}).get("rss", [])
        all_items = fetch_all_rss_sources(rss_sources)
        print(f"  Fetched {len(all_items)} total items")
        
        # 5. Filter and select content
        print("\n[5/8] Filtering and selecting content...")
        filters = config.get("filters", {})
        
        filtered = filter_items(
            items=all_items,
            block_keywords=filters.get("block_keywords", []),
            boost_keywords=filters.get("boost_keywords", []),
            used_urls=used_urls,
        )
        print(f"  After filtering: {len(filtered)} items")
        
        selected = select_items(
            items=filtered,
            max_items=filters.get("global_max_items", 6),
            max_per_source=filters.get("max_per_source", 2),
        )
        print(f"  Selected {len(selected)} items for today's episode:")
        
        for item in selected:
            print(f"    - [{item.source}] {item.title[:50]}...")
        
        if len(selected) == 0:
            print("\n  ERROR: No content items available for today's episode")
            return False
        
        # 6. Generate script
        print("\n[6/8] Generating script...")
        if dry_run:
            script_result = generate_script_dry_run(weather_text, selected, config)
            print("  [DRY RUN] Generated placeholder script")
        else:
            script_result = generate_script(weather_text, selected, config)
            print(f"  Generated script ({len(script_result['script'])} characters)")
        
        script = script_result["script"]
        
        if verbose:
            print("\n--- SCRIPT START ---")
            print(script)
            print("--- SCRIPT END ---\n")
        
        # Estimate duration
        tts_config = config.get("openai", {}).get("tts", {})
        speed = tts_config.get("speed", 1.0)
        estimated_duration = estimate_audio_duration(script, speed)
        print(f"  Estimated duration: {estimated_duration:.1f} minutes")
        
        # Get today's date (used for filenames and transcript)
        today = datetime.now()
        
        # Save transcript with references and prompts
        transcript_path = save_transcript(
            date=today,
            script_result=script_result,
            items=selected,
            config=config,
            estimated_duration=estimated_duration,
        )
        print(f"  Saved transcript to: {transcript_path}")
        
        # Upload transcript to R2 (not in dry run)
        if not dry_run:
            transcript_content = transcript_path.read_text(encoding="utf-8")
            transcript_filename = f"{today.strftime('%Y-%m-%d')}.txt"
            transcript_url = upload_transcript_to_r2(transcript_content, transcript_filename, config)
            print(f"  Uploaded transcript to: {transcript_url}")
        else:
            print("  [DRY RUN] Would upload transcript to R2")
        
        # 7. Synthesize audio
        print("\n[7/8] Synthesizing audio...")
        if dry_run:
            mp3_bytes = b""  # Empty for dry run
            print("  [DRY RUN] Skipped TTS synthesis")
        else:
            mp3_bytes = synthesize_mp3(script, config)
            print(f"  Generated MP3 ({len(mp3_bytes)} bytes)")
        
        # 8. Upload and update feed
        print("\n[8/8] Uploading and updating feed...")
        filename = f"{today.strftime('%Y-%m-%d')}.mp3"
        
        if dry_run:
            mp3_url = f"https://example.com/episodes/{filename}"
            print(f"  [DRY RUN] Would upload to: {mp3_url}")
        else:
            # Check R2 connection first
            if not check_r2_connection(config):
                print("  ERROR: Cannot connect to R2 storage")
                return False
            
            mp3_url = upload_mp3_to_r2(mp3_bytes, filename, config)
            print(f"  Uploaded to: {mp3_url}")
        
        # Fetch NASA APOD for episode artwork
        episode_image_url = None
        apod_data = get_apod_for_episode()
        if apod_data:
            episode_image_url = apod_data.get("image_url")
            print(f"  NASA APOD: {apod_data.get('image_title', 'N/A')}")
        else:
            print("  NASA APOD: Not available (may be a video today)")
        
        # Create episode metadata with show notes
        episode = create_episode_metadata(
            date=today,
            mp3_url=mp3_url,
            mp3_size=len(mp3_bytes),
            duration_seconds=estimated_duration * 60,
            config=config,
            items=selected,  # Include items for rich show notes
            episode_image_url=episode_image_url,  # NASA APOD as episode artwork
        )
        
        # Update RSS feed
        SITE_DIR.mkdir(parents=True, exist_ok=True)
        feed_xml = update_feed(str(FEED_PATH), episode, config)
        save_feed(str(FEED_PATH), feed_xml)
        print(f"  Updated feed at: {FEED_PATH}")
        
        # Regenerate landing page from config
        save_index_html(config, SITE_DIR)
        print(f"  Updated site at: {SITE_DIR / 'index.html'}")
        
        # Update state with used URLs
        now = datetime.now().isoformat()
        if "url_timestamps" not in state:
            state["url_timestamps"] = {}
        
        for item in selected:
            state["url_timestamps"][item.url] = now
        
        state["used_urls"] = list(state["url_timestamps"].keys())
        state["last_run"] = now
        save_state(state)
        print(f"  Updated state with {len(selected)} new URLs")
        
        print("\n" + "=" * 60)
        print("SUCCESS! Today's episode is ready.")
        print("=" * 60)
        
        return True
    
    except Exception as e:
        print(f"\n\nERROR: Pipeline failed with exception:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Vibecast - Daily podcast generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m podcast.run_daily              # Run full pipeline
  python -m podcast.run_daily --dry-run    # Test without API calls
  python -m podcast.run_daily -v           # Verbose output with script
        """,
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making API calls or uploads",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print verbose output including generated script",
    )
    
    args = parser.parse_args()
    
    success = run_pipeline(dry_run=args.dry_run, verbose=args.verbose)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

