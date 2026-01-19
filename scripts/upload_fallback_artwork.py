#!/usr/bin/env python3
"""One-time script to upload the fallback artwork image to R2.

Usage:
    python scripts/upload_fallback_artwork.py

Requires R2 credentials to be set in environment:
    - R2_ACCOUNT_ID
    - R2_ACCESS_KEY_ID
    - R2_SECRET_ACCESS_KEY
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from podcast.run_daily import load_config
from podcast.storage import upload_fallback_artwork_to_r2, check_r2_connection


def main():
    # Possible locations for the fallback image
    possible_paths = [
        Path(__file__).parent.parent / "docs" / "default-episode-art.png",
        Path(__file__).parent.parent / "docs" / "AI_Gen_Image_Art.jpeg",
        Path(__file__).parent.parent / "docs" / "AI_Gen_Image_Art.png",
    ]
    
    # Find the image
    image_path = None
    for path in possible_paths:
        if path.exists():
            image_path = path
            break
    
    if not image_path:
        print("ERROR: Could not find fallback artwork image.")
        print("Expected one of:")
        for path in possible_paths:
            print(f"  - {path}")
        print("\nPlease save your fallback image to one of these locations.")
        sys.exit(1)
    
    print(f"Found fallback image: {image_path}")
    
    # Load config
    print("Loading configuration...")
    config = load_config()
    
    # Check R2 connection
    print("Checking R2 connection...")
    if not check_r2_connection(config):
        print("ERROR: Cannot connect to R2. Check your credentials.")
        sys.exit(1)
    
    # Read the image
    print(f"Reading image ({image_path.stat().st_size} bytes)...")
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    # Upload to R2
    print("Uploading to R2...")
    artwork_config = config.get("artwork", {})
    fallback_key = artwork_config.get("r2_fallback_key", "static/default-episode-art.png")
    print(f"  Target key: {fallback_key}")
    
    url = upload_fallback_artwork_to_r2(image_bytes, config)
    
    print(f"\n✓ Fallback artwork uploaded successfully!")
    print(f"  URL: {url}")
    print(f"\nThis URL will be used when AI artwork generation fails.")


if __name__ == "__main__":
    main()
