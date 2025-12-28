#!/usr/bin/env python3
"""
Configuration validator for Vibecast.
Checks if you're using template/placeholder values that should be customized.
"""

import yaml
import sys
import os
from pathlib import Path

def check_config():
    """Check config.yaml for template values that need customization."""
    
    config_path = Path("podcast/config.yaml")
    if not config_path.exists():
        print("❌ Error: podcast/config.yaml not found")
        return False
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    warnings = []
    errors = []
    
    # Check podcast metadata
    podcast = config.get("podcast", {})
    author = os.getenv("VIBECAST_AUTHOR") or podcast.get("author", "")
    github_url = podcast.get("github_url", "")
    
    if author in ["Your Name", "", "Dominic", "Dominic Critchlow"]:
        warnings.append("📝 podcast.author is set to a template value. Update it or set VIBECAST_AUTHOR")
    
    if "YOUR_USERNAME" in github_url or "domcritchlow" in github_url:
        warnings.append("🔗 podcast.github_url should point to your fork, not the original repo")
    
    # Check location
    location = config.get("location", {})
    loc_name = os.getenv("VIBECAST_LOCATION_NAME") or location.get("name", "")
    loc_lat = float(os.getenv("VIBECAST_LOCATION_LAT") or location.get("lat", 0))
    loc_lon = float(os.getenv("VIBECAST_LOCATION_LON") or location.get("lon", 0))
    
    if loc_name in ["Your City", ""] or (loc_lat == 0.0 and loc_lon == 0.0):
        errors.append("📍 Location not configured! Set location in config.yaml or via environment variables")
    
    # Check for API keys (environment only - never in config)
    if not os.getenv("OPENAI_API_KEY"):
        errors.append("🔑 OPENAI_API_KEY not set in environment")
    
    if not os.getenv("R2_ACCOUNT_ID"):
        errors.append("☁️  R2_ACCOUNT_ID not set in environment")
    
    # Print results
    print("\n" + "="*60)
    print("🔍 Vibecast Configuration Check")
    print("="*60 + "\n")
    
    if errors:
        print("❌ ERRORS (must fix before running):\n")
        for error in errors:
            print(f"  {error}")
        print()
    
    if warnings:
        print("⚠️  WARNINGS (recommended to fix):\n")
        for warning in warnings:
            print(f"  {warning}")
        print()
    
    if not errors and not warnings:
        print("✅ Configuration looks good!")
        print("   All required values are set.\n")
        return True
    
    if errors:
        print("\n💡 Tip: Copy .env.example to .env and fill in your values")
        print("   Or set GitHub Secrets if running via Actions\n")
        return False
    
    if warnings:
        print("\n💡 Tip: These warnings won't stop the podcast from running,")
        print("   but you should update them to make it truly yours.\n")
        return True

if __name__ == "__main__":
    success = check_config()
    sys.exit(0 if success else 1)

