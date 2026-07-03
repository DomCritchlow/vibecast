#!/usr/bin/env python3
"""Regenerate all outputs (RSS feed + website) from episode JSON metadata.

This is the main script to use after:
- Creating/editing episode JSON files
- Changing templates
- Updating configuration

Fast, reliable, single source of truth.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def run_script(script_name: str) -> bool:
    """Run a Python script and return success status."""
    script_path = SCRIPT_DIR / script_name

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)], check=True, capture_output=False
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error running {script_name}: {e}")
        return False


def main():
    """Main entry point."""
    print("=" * 70)
    print("REGENERATE ALL OUTPUTS FROM EPISODE METADATA")
    print("=" * 70)
    print()
    print("This regenerates:")
    print("  1. RSS feed (from podcast/episodes/*.json)")
    print("  2. Website pages (from templates/)")
    print()

    # Step 1: Generate RSS feed
    print("[1/2] Generating RSS feed...")
    if not run_script("generate_feed.py"):
        return 1

    # Step 2: Generate website
    print("\n[2/2] Generating website...")
    if not run_script("generate_site.py"):
        return 1

    print("\n" + "=" * 70)
    print("✓ COMPLETE: All outputs regenerated")
    print("=" * 70)
    print()
    print("Generated files:")
    print("  - docs/feed.xml")
    print("  - docs/index.html")
    print("  - docs/about.html")
    print("  - docs/docs.html")
    print()
    print("Ready to commit and deploy!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
