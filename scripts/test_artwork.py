#!/usr/bin/env python3
"""Test script for artwork generation.

Usage:
    # Generate artwork for today with mock items
    python scripts/test_artwork.py
    
    # Generate for a specific date
    python scripts/test_artwork.py --date 2025-01-15
    
    # Save locally instead of uploading to R2
    python scripts/test_artwork.py --local
    
    # Just generate the brief and prompt (no image generation)
    python scripts/test_artwork.py --dry-run
    
    # Use real items from RSS feeds
    python scripts/test_artwork.py --fetch-real

Requires environment variables:
    - OPENAI_API_KEY (always required)
    - R2_* credentials (unless using --local)
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from podcast.run_daily import load_config
from podcast.artwork.brief import generate_art_brief, select_accent_color
from podcast.artwork.prompt import render_artwork_prompt
from podcast.artwork.generator import get_artwork_provider, generate_and_publish_episode_artwork


@dataclass
class MockItem:
    """Mock content item for testing."""
    title: str
    source: str
    summary: str = ""
    url: str = ""


# Sample episode items for testing different themes
SAMPLE_EPISODES = {
    "tech": [
        MockItem("OpenAI releases GPT-5 with improved reasoning capabilities", "OpenAI News"),
        MockItem("NASA's Artemis mission successfully lands humans on Mars", "NASA Science"),
        MockItem("New quantum computer achieves 1000-qubit milestone", "MIT Tech Review"),
        MockItem("Electric aircraft completes first transatlantic flight", "Ars Technica"),
    ],
    "science": [
        MockItem("Scientists discover high-temperature superconductor at room temperature", "Nature"),
        MockItem("James Webb captures most detailed image of distant galaxy", "NASA JPL"),
        MockItem("CRISPR therapy successfully treats genetic blindness", "Quanta Magazine"),
        MockItem("Ocean cleanup project removes 1 million tons of plastic", "Positive News"),
    ],
    "space": [
        MockItem("SpaceX Starship completes first orbital refueling mission", "Space.com"),
        MockItem("Astronomers detect signs of life in Venus atmosphere", "NASA Science"),
        MockItem("China launches permanent lunar base construction", "Ars Technica"),
        MockItem("First commercial space hotel opens for reservations", "The Verge"),
    ],
    "mixed": [
        MockItem("AI system solves 50-year-old math problem", "Quanta Magazine"),
        MockItem("Global renewable energy exceeds fossil fuels for first time", "Positive News"),
        MockItem("Breakthrough in fusion energy achieves net positive output", "MIT Tech Review"),
        MockItem("New cancer vaccine shows 90% effectiveness in trials", "Nature"),
    ],
}


def fetch_real_items(config):
    """Fetch real items from RSS feeds."""
    from podcast.sources.rss import fetch_all_rss_sources
    from podcast.sources.base import filter_items, select_items
    
    print("Fetching real RSS items...")
    rss_sources = config.get("sources", {}).get("rss", [])
    all_items = fetch_all_rss_sources(rss_sources)
    
    filters = config.get("filters", {})
    filtered = filter_items(
        items=all_items,
        block_keywords=filters.get("block_keywords", []),
        boost_keywords=filters.get("boost_keywords", []),
        used_urls=set(),
    )
    
    selected = select_items(
        items=filtered,
        max_items=filters.get("global_max_items", 6),
        max_per_source=filters.get("max_per_source", 2),
    )
    
    print(f"Selected {len(selected)} items:")
    for item in selected:
        print(f"  - [{item.source}] {item.title[:50]}...")
    
    return selected


def main():
    parser = argparse.ArgumentParser(description="Test artwork generation")
    parser.add_argument("--date", type=str, help="Episode date (YYYY-MM-DD)", 
                        default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--theme", type=str, choices=list(SAMPLE_EPISODES.keys()),
                        default="mixed", help="Sample episode theme")
    parser.add_argument("--local", action="store_true", 
                        help="Save locally instead of uploading to R2")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only generate brief and prompt, no image")
    parser.add_argument("--fetch-real", action="store_true",
                        help="Use real RSS items instead of samples")
    parser.add_argument("--output", type=str, default="test_artwork.png",
                        help="Output filename for --local mode")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("ARTWORK GENERATION TEST")
    print("=" * 60)
    
    # Load config
    print("\nLoading configuration...")
    config = load_config()
    
    # Get items
    if args.fetch_real:
        items = fetch_real_items(config)
    else:
        items = SAMPLE_EPISODES[args.theme]
        print(f"\nUsing sample '{args.theme}' theme:")
        for item in items:
            print(f"  - [{item.source}] {item.title[:50]}...")
    
    episode_id = args.date
    print(f"\nEpisode ID: {episode_id}")
    
    # Step 1: Generate art brief
    print("\n" + "-" * 40)
    print("STEP 1: Generating Art Brief")
    print("-" * 40)
    
    brief = generate_art_brief(items, episode_id, config)
    
    print(f"\nMood: {', '.join(brief.mood_adjectives)}")
    print(f"Scene: {brief.single_scene_metaphor}")
    print(f"Detail: {brief.secondary_detail}")
    print(f"Accent: {brief.accent_color}")
    
    # Step 2: Render prompt
    print("\n" + "-" * 40)
    print("STEP 2: Rendering Prompt")
    print("-" * 40)
    
    prompt, negative_prompt = render_artwork_prompt(brief, config)
    
    print(f"\n{prompt}")
    print(f"\n[Negative prompt]: {negative_prompt[:100]}...")
    
    if args.dry_run:
        print("\n[DRY RUN] Stopping before image generation")
        return
    
    # Step 3: Generate image
    print("\n" + "-" * 40)
    print("STEP 3: Generating Image")
    print("-" * 40)
    
    provider = get_artwork_provider(config)
    artwork_config = config.get("artwork", {})
    size = artwork_config.get("size", 1024)
    
    print(f"\nUsing provider: {provider.name}")
    print(f"Size: {size}x{size}")
    print(f"Quality: {artwork_config.get('quality', 'medium')}")
    print("\nGenerating image (this may take 10-30 seconds)...")
    
    image_bytes = provider.generate(prompt=prompt, size=size)
    
    print(f"Generated: {len(image_bytes)} bytes")
    
    # Step 4: Save or upload
    if args.local:
        print("\n" + "-" * 40)
        print("STEP 4: Saving Locally")
        print("-" * 40)
        
        output_path = Path(args.output)
        output_path.write_bytes(image_bytes)
        print(f"\nSaved to: {output_path.absolute()}")
    else:
        print("\n" + "-" * 40)
        print("STEP 4: Uploading to R2")
        print("-" * 40)
        
        from podcast.storage import upload_artwork_to_r2, upload_artwork_metadata_to_r2
        
        artwork_url = upload_artwork_to_r2(episode_id, image_bytes, config)
        print(f"\nUploaded to: {artwork_url}")
        
        # Save metadata
        metadata = {
            "episode_id": episode_id,
            "generated_at": datetime.now().isoformat(),
            "provider": provider.name,
            "brief": brief.to_dict(),
            "test_mode": True,
            "theme": args.theme if not args.fetch_real else "real_rss",
        }
        upload_artwork_metadata_to_r2(episode_id, metadata, prompt, config)
        print("Metadata saved")
    
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
