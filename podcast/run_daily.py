#!/usr/bin/env python3
"""Main orchestrator for Vibecast daily podcast generation.

The pipeline runs as discrete steps with per-step error policy:
required steps (content, script, audio, upload) abort the run with a clear
error; optional steps (weather, artwork, newspaper) degrade gracefully.
"""

import argparse
import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from .artwork import generate_and_publish_episode_artwork
from .episode_store import save_episode
from .models import Episode, validate_config
from .newspaper import _color_name_to_hex, generate_newspaper_pdf
from .rss_feed import generate_feed_from_store, save_feed
from .site_generator import save_site_pages
from .sources.base import ContentItem, filter_items, select_items
from .sources.reading_list import fetch_reading_list
from .sources.rss import fetch_all_rss_sources
from .sources.weather import fetch_weather, format_weather_for_script
from .storage import (
    check_r2_connection,
    upload_mp3_to_r2,
    upload_newspaper_to_r2,
    upload_transcript_to_r2,
)
from .tts import estimate_duration, synthesize_speech
from .writer import generate_episode_title, generate_script, generate_script_dry_run

logger = logging.getLogger("vibecast")

# Paths relative to this file
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
STATE_PATH = SCRIPT_DIR / "state.json"
SITE_DIR = SCRIPT_DIR.parent / "docs"
FEED_PATH = SITE_DIR / "feed.xml"
SCRIPTS_DIR = SITE_DIR / "scripts"

DEFAULT_URL_RETENTION_DAYS = 90


class PipelineError(RuntimeError):
    """A required pipeline step failed."""


# ---------------------------------------------------------------------------
# Config and state
# ---------------------------------------------------------------------------


def load_config() -> dict:
    """Load configuration from config.yaml with environment variable overrides."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    config = _apply_env_overrides(config)
    return validate_config(config)


def _apply_env_overrides(config: dict) -> dict:
    """Apply environment variable overrides to config.

    This allows personal settings to be kept out of the committed config.yaml
    while still having sensible defaults for others who clone the repo.
    """
    if os.environ.get("VIBECAST_LOCATION_NAME"):
        config["location"]["name"] = os.environ["VIBECAST_LOCATION_NAME"]
    if os.environ.get("VIBECAST_LOCATION_LAT"):
        config["location"]["lat"] = float(os.environ["VIBECAST_LOCATION_LAT"])
    if os.environ.get("VIBECAST_LOCATION_LON"):
        config["location"]["lon"] = float(os.environ["VIBECAST_LOCATION_LON"])

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

    if os.environ.get("VIBECAST_R2_PUBLIC_URL"):
        config["storage"]["r2"]["public_base_url"] = os.environ["VIBECAST_R2_PUBLIC_URL"]

    if os.environ.get("VIBECAST_TIMEZONE"):
        config["schedule"]["timezone"] = os.environ["VIBECAST_TIMEZONE"]

    return config


def load_state() -> dict:
    """Load state from state.json (URL timestamps for deduplication)."""
    if not STATE_PATH.exists():
        return {"url_timestamps": {}, "last_run": None}

    try:
        with open(STATE_PATH) as f:
            state = json.load(f)
    except json.JSONDecodeError:
        return {"url_timestamps": {}, "last_run": None}

    # Migrate legacy state: used_urls without timestamps
    state.setdefault("url_timestamps", {})
    for url in state.pop("used_urls", []):
        state["url_timestamps"].setdefault(url, "1970-01-01T00:00:00")
    return state


def prune_state(state: dict, retention_days: int) -> dict:
    """Drop URL history older than the retention window so state.json stays small."""
    cutoff = datetime.now() - timedelta(days=retention_days)
    kept = {}
    for url, timestamp in state.get("url_timestamps", {}).items():
        try:
            seen = datetime.fromisoformat(timestamp)
        except ValueError:
            continue
        if seen >= cutoff:
            kept[url] = timestamp
    dropped = len(state.get("url_timestamps", {})) - len(kept)
    if dropped:
        logger.info("Pruned %d URLs older than %d days from state", dropped, retention_days)
    state["url_timestamps"] = kept
    return state


def save_state(state: dict) -> None:
    """Save state to state.json."""
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Transcript
# ---------------------------------------------------------------------------


def save_transcript(
    date: datetime,
    script_result: dict,
    items: list[ContentItem],
    config: dict,
    estimated_duration: float,
    reading_items: list | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Save the episode transcript with prompts, script, and references."""
    target_dir = output_dir or SCRIPTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    filepath = target_dir / f"{date.strftime('%Y-%m-%d')}.txt"

    podcast = config.get("podcast", {})
    vibe = config.get("vibe", {})

    lines = [
        "=" * 40,
        "VIBECAST TRANSCRIPT",
        f"{vibe.get('name', 'Episode')} — {date.strftime('%A, %B %d, %Y')}",
        "=" * 40,
        "",
        "EPISODE SUMMARY",
        "-" * 30,
        f"Date: {date.strftime('%Y-%m-%d')}",
        f"Duration: ~{estimated_duration:.1f} minutes",
        f"Model: {script_result.get('model', 'unknown')}",
        f"Stories covered: {len(items)}",
        "",
        "Sources featured in this episode:",
    ]

    sources_seen = set()
    for item in items:
        if item.source not in sources_seen:
            lines.append(f"  • {item.source}")
            sources_seen.add(item.source)

    lines.extend(["", "", "FULL SCRIPT", "-" * 30, "", script_result.get("script", ""), "", ""])

    lines.extend(["REFERENCES", "-" * 30, "Links to the stories mentioned in this episode:", ""])
    for i, item in enumerate(items, 1):
        lines.extend(
            [f"{i}. {item.title}", f"   Source: {item.source}", f"   Link: {item.url}", ""]
        )

    if reading_items:
        lines.extend(
            ["", "READING LIST", "-" * 30, "Articles recommended for further reading:", ""]
        )
        for i, item in enumerate(reading_items, 1):
            author_info = f" by {item.author}" if getattr(item, "author", "") else ""
            lines.extend(
                [
                    f"{i}. {item.title}{author_info}",
                    f"   Source: {item.source}",
                    f"   Link: {item.url}",
                    "",
                ]
            )

    lines.extend(
        [
            "",
            "",
            "PROMPTS USED",
            "=" * 70,
            "",
            "SYSTEM PROMPT",
            "-" * 40,
            "",
            script_result.get("system_prompt", ""),
            "",
            "",
            "USER PROMPT",
            "-" * 40,
            "",
            script_result.get("user_prompt", ""),
            "",
            "",
            "-" * 70,
            f"Generated by Vibecast • {podcast.get('site_url', '')}",
            "-" * 70,
        ]
    )

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


def step_weather(config: dict) -> str:
    """Fetch weather; degrades to a fallback sentence on failure."""
    location = config.get("location", {})
    lat = location.get("lat", 0.0)
    lon = location.get("lon", 0.0)
    name = location.get("name", "your area")

    if lat == 0.0 and lon == 0.0:
        logger.warning("Location not configured, skipping weather")
        return "Weather information is not available today."

    weather_config = config.get("sources", {}).get("weather", {})
    weather_data = fetch_weather(
        lat=lat,
        lon=lon,
        units=location.get("units", "fahrenheit"),
        include_forecast=weather_config.get("include_forecast", True),
        forecast_days=weather_config.get("forecast_days", 1),
    )

    if not weather_data:
        logger.warning("Weather fetch failed, using fallback")
        return f"Weather for {name} is currently unavailable."

    weather_text = format_weather_for_script(weather_data, name)
    logger.info("Weather: %s", weather_text[:80])
    return weather_text


def step_content(config: dict, used_urls: set[str]) -> tuple[list[ContentItem], list]:
    """Fetch, filter, and select today's stories plus the reading list."""
    rss_sources = config.get("sources", {}).get("rss", [])
    all_items = fetch_all_rss_sources(rss_sources)
    logger.info("Fetched %d total items", len(all_items))

    reading_items = fetch_reading_list(config, used_urls) or []

    filters = config.get("filters", {})
    filtered = filter_items(
        items=all_items,
        block_keywords=filters.get("block_keywords", []),
        boost_keywords=filters.get("boost_keywords", []),
        used_urls=used_urls,
    )
    logger.info("After filtering: %d items", len(filtered))

    selected = select_items(
        items=filtered,
        max_items=filters.get("global_max_items", 6),
        max_per_source=filters.get("max_per_source", 2),
    )
    for item in selected:
        logger.info("Selected: [%s] %s", item.source, item.title[:60])

    if not selected:
        raise PipelineError("No content items available for today's episode")

    return selected, reading_items


def step_artwork(
    episode_id: str, selected: list[ContentItem], episode_title: str, config: dict, dry_run: bool
) -> tuple[str | None, str]:
    """Generate episode artwork; degrades to the fallback image on failure."""
    artwork_config = config.get("artwork", {})
    default_color = artwork_config.get("accent_palette", ["burnt orange"])[0]

    if dry_run:
        public_base_url = (
            config.get("storage", {}).get("r2", {}).get("public_base_url", "https://example.com")
        )
        return f"{public_base_url}/episodes/{episode_id}/episode-art.png", default_color

    if not artwork_config.get("enabled", True):
        logger.info("Episode artwork disabled in config")
        return None, default_color

    episode_context = {"episode_id": episode_id, "items": selected, "title": episode_title}
    try:
        return generate_and_publish_episode_artwork(episode_context, config)
    except Exception as e:
        logger.warning("Artwork generation failed: %s", e)
        return None, default_color


def step_newspaper(
    today: datetime,
    selected: list[ContentItem],
    config: dict,
    weather_text: str,
    reading_items: list,
    estimated_duration: float,
    episode_image_url: str | None,
    accent_color: str,
    dry_run: bool,
) -> str | None:
    """Generate + upload the newspaper PDF; optional, degrades to None."""
    episode_id = today.strftime("%Y-%m-%d")

    if dry_run:
        public_base_url = (
            config.get("storage", {}).get("r2", {}).get("public_base_url", "https://example.com")
        )
        return f"{public_base_url}/episodes/{episode_id}/newspaper.pdf"

    try:
        pdf_path = generate_newspaper_pdf(
            date=today,
            items=selected,
            config=config,
            weather_text=weather_text,
            reading_items=reading_items,
            duration_minutes=estimated_duration,
            episode_artwork_url=episode_image_url,
            accent_color=_color_name_to_hex(accent_color),
        )
        if not pdf_path:
            return None

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        newspaper_url = upload_newspaper_to_r2(episode_id, pdf_bytes, config)
        logger.info("Newspaper: %s", newspaper_url)
        return newspaper_url
    except Exception as e:
        logger.warning("Newspaper generation/upload failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run_pipeline(dry_run: bool = False, verbose: bool = False) -> bool:
    """Run the complete podcast generation pipeline."""
    logger.info("=" * 60)
    logger.info("VIBECAST - Daily Podcast Generator")
    logger.info("=" * 60)

    if dry_run:
        logger.info("[DRY RUN MODE - No API calls or uploads will be made]")

    try:
        # 1. Config + state
        logger.info("[1/8] Loading configuration and state...")
        config = load_config()
        logger.info(
            "Vibe: %s | Podcast: %s", config["vibe"].get("name"), config["podcast"].get("title")
        )

        state = load_state()
        retention_days = config.get("filters", {}).get(
            "url_retention_days", DEFAULT_URL_RETENTION_DAYS
        )
        state = prune_state(state, retention_days)
        used_urls = set(state["url_timestamps"].keys())
        logger.info("Deduplicating against %d recently used URLs", len(used_urls))

        today = datetime.now()
        episode_id = today.strftime("%Y-%m-%d")

        # 2. Weather (optional)
        logger.info("[2/8] Fetching weather...")
        weather_text = step_weather(config)

        # 3. Content (required)
        logger.info("[3/8] Fetching and selecting content...")
        selected, reading_items = step_content(config, used_urls)

        # 4. Script + title (required)
        logger.info("[4/8] Generating script...")
        if dry_run:
            script_result = generate_script_dry_run(weather_text, selected, config, reading_items)
            episode_title = "AI-Generated Title Here"
        else:
            script_result = generate_script(weather_text, selected, config, reading_items)
            episode_title = generate_episode_title(selected, config)
        script = script_result["script"]
        logger.info("Script: %d characters | Title: %s", len(script), episode_title)

        if verbose:
            logger.info("--- SCRIPT START ---\n%s\n--- SCRIPT END ---", script)

        tts_config = config.get("tts", {})
        provider = tts_config.get("provider", "openai")
        provider_config = tts_config.get(provider, {})
        estimated_duration = estimate_duration(script, provider_config.get("speed", 1.0))
        logger.info("Estimated duration: %.1f minutes", estimated_duration)

        # 5. Transcript
        logger.info("[5/8] Saving transcript...")
        transcript_path = save_transcript(
            date=today,
            script_result=script_result,
            items=selected,
            config=config,
            estimated_duration=estimated_duration,
            reading_items=reading_items,
            # Don't overwrite a real transcript with placeholder content
            output_dir=Path(tempfile.gettempdir()) / "vibecast-dry-run" if dry_run else None,
        )
        logger.info("Saved transcript to %s", transcript_path)

        if not dry_run:
            transcript_url = upload_transcript_to_r2(
                transcript_path.read_text(encoding="utf-8"), f"{episode_id}.txt", config
            )
            logger.info("Uploaded transcript: %s", transcript_url)

        # 6. Audio (required)
        logger.info("[6/8] Synthesizing audio with %s...", provider)
        if dry_run:
            mp3_bytes = b""
        else:
            mp3_bytes = synthesize_speech(script, config)
            logger.info("Generated MP3 (%d bytes)", len(mp3_bytes))

        # 7. Upload audio (required)
        logger.info("[7/8] Uploading audio...")
        filename = f"{episode_id}.mp3"
        if dry_run:
            mp3_url = f"https://example.com/episodes/{filename}"
        else:
            if not check_r2_connection(config):
                raise PipelineError("Cannot connect to R2 storage")
            mp3_url = upload_mp3_to_r2(mp3_bytes, filename, config)
            logger.info("Uploaded audio: %s", mp3_url)

        # Artwork + newspaper (optional)
        episode_image_url, accent_color = step_artwork(
            episode_id, selected, episode_title, config, dry_run
        )
        newspaper_url = step_newspaper(
            today,
            selected,
            config,
            weather_text,
            reading_items,
            estimated_duration,
            episode_image_url,
            accent_color,
            dry_run,
        )

        # 8. Persist metadata + regenerate feed and site
        logger.info("[8/8] Saving episode and regenerating feed/site...")
        r2_public_url = config.get("storage", {}).get("r2", {}).get("public_base_url", "")

        episode_json = {
            "guid": episode_id,
            "date": today.isoformat(),
            "title": episode_title,
            "tagline": config.get("podcast", {}).get("tagline", "Your daily podcast"),
            "duration_seconds": estimated_duration * 60,
            "duration_formatted": f"{int(estimated_duration)}:{int((estimated_duration % 1) * 60):02d}",
            "media": {
                "audio_url": mp3_url,
                "audio_size_bytes": len(mp3_bytes),
                "artwork_url": episode_image_url,
                "newspaper_url": newspaper_url,
                "transcript_url": f"{r2_public_url.rstrip('/')}/transcripts/{episode_id}.txt",
            },
            "stories": [
                {
                    "title": item.title,
                    "source": item.source,
                    "url": item.url,
                    "summary": item.summary,
                }
                for item in selected
            ],
            "reading_list": [
                {
                    "title": item.title,
                    "author": getattr(item, "author", ""),
                    "source": item.source,
                    "url": item.url,
                    "description": getattr(item, "description", ""),
                }
                for item in reading_items
            ],
            "metadata": {
                "created_at": today.isoformat(),
                "llm_provider": script_result.get("provider", "unknown"),
                "llm_model": script_result.get("model", "unknown"),
                "tts_provider": provider,
                "tts_voice": provider_config.get("voice") or provider_config.get("voice_id") or "",
            },
        }

        if dry_run:
            # Validate the episode shape but don't pollute the store,
            # feed, site, or state with placeholder data.
            Episode.model_validate(episode_json)
            logger.info("[DRY RUN] Episode JSON validates; skipping save/feed/site/state writes")
        else:
            json_path = save_episode(episode_json)
            logger.info("Saved episode JSON: %s", json_path)

            # Regenerate feed.xml in full from the episode store
            SITE_DIR.mkdir(parents=True, exist_ok=True)
            save_feed(str(FEED_PATH), generate_feed_from_store(config))
            logger.info("Updated feed: %s", FEED_PATH)

            save_site_pages(config, SITE_DIR)
            logger.info("Updated site: %s", SITE_DIR / "index.html")

            # Record used URLs
            now = today.isoformat()
            for item in [*selected, *reading_items]:
                state["url_timestamps"][item.url] = now
            state["last_run"] = now
            save_state(state)
            logger.info(
                "Updated state with %d new URLs (%d stories + %d reading list)",
                len(selected) + len(reading_items),
                len(selected),
                len(reading_items),
            )

        logger.info("=" * 60)
        logger.info("SUCCESS! Today's episode is ready.")
        logger.info("=" * 60)
        return True

    except Exception:
        logger.exception("Pipeline failed")
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

    parser.add_argument("--dry-run", action="store_true", help="Run without API calls or uploads")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output including generated script"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-7s %(name)s: %(message)s",
    )
    # Quiet down chatty third-party loggers
    for noisy in ("httpx", "httpcore", "botocore", "boto3", "urllib3", "openai", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    success = run_pipeline(dry_run=args.dry_run, verbose=args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
