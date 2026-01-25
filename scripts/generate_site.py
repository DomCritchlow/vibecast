#!/usr/bin/env python3
"""Generate static site pages from episode JSON metadata and templates.

This reads from podcast/episodes/*.json and podcast/templates/
and generates docs/*.html.
"""

import sys
import os
from pathlib import Path

# Add parent dir to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

import yaml
from podcast.site_generator import save_site_pages


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


def main():
    """Main entry point."""
    print("=" * 70)
    print("GENERATE SITE PAGES FROM TEMPLATES")
    print("=" * 70)
    print()
    
    # Load config
    print("Loading configuration...")
    config = load_config()
    
    # Generate pages
    site_dir = SCRIPT_DIR.parent / "docs"
    print(f"\nGenerating pages in: {site_dir}")
    
    save_site_pages(config, site_dir)
    
    print("\n✓ All pages generated successfully")
    print()
    print("Pages generated:")
    print("  - index.html (from templates/index.html)")
    print("  - about.html (from templates/about.html)")
    print("  - docs.html (from templates/docs.html)")
    print()
    print("Note: episode.html loads data dynamically from feed.xml")
    
    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
