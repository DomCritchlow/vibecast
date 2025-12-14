"""NASA image sources - APOD and Image Library for episode artwork."""

import random
import requests
from datetime import datetime
from typing import Optional


# Search terms for NASA Image Library fallback (space/nature themed)
NASA_SEARCH_TERMS = [
    "earth from space",
    "sunrise from space",
    "nebula",
    "galaxy",
    "aurora",
    "moon",
    "saturn",
    "jupiter",
    "milky way",
    "hubble",
    "james webb",
    "international space station",
    "blue marble",
]


def fetch_apod() -> Optional[dict]:
    """Fetch today's NASA Astronomy Picture of the Day.
    
    The APOD API is free and doesn't require an API key for basic use
    (limited to 30 requests/hour per IP without a key).
    
    Returns:
        Dictionary with image data, or None if request fails.
        {
            "title": "Image title",
            "explanation": "Description of the image",
            "url": "URL to the image (may be video on some days)",
            "hdurl": "High-resolution image URL (if available)",
            "media_type": "image" or "video",
            "date": "2025-12-14",
            "copyright": "Photographer name (if applicable)"
        }
    """
    api_url = "https://api.nasa.gov/planetary/apod"
    
    params = {
        "api_key": "DEMO_KEY",  # Free demo key, 30 requests/hour limit
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "title": data.get("title", ""),
            "explanation": data.get("explanation", ""),
            "url": data.get("url", ""),
            "hdurl": data.get("hdurl", ""),
            "media_type": data.get("media_type", "image"),
            "date": data.get("date", ""),
            "copyright": data.get("copyright", "NASA"),
        }
    
    except requests.RequestException as e:
        print(f"NASA APOD API error: {e}")
        return None


def get_apod_image_url() -> Optional[str]:
    """Get just the image URL from today's APOD.
    
    Returns the standard resolution URL, or None if:
    - API request fails
    - Today's APOD is a video instead of image
    
    Returns:
        Image URL string, or None.
    """
    apod = fetch_apod()
    
    if not apod:
        return None
    
    # Skip if today's APOD is a video
    if apod.get("media_type") != "image":
        print("Today's NASA APOD is a video, skipping image")
        return None
    
    # Prefer standard URL over HD (faster loading, smaller size)
    return apod.get("url") or apod.get("hdurl")


def fetch_nasa_image_library(search_term: Optional[str] = None) -> Optional[dict]:
    """Fetch a random image from NASA Image and Video Library.
    
    This is a fallback when APOD is a video or unavailable.
    Free API, no key required.
    
    Args:
        search_term: Optional search term. If None, picks randomly from NASA_SEARCH_TERMS.
    
    Returns:
        Dictionary with image data, or None if request fails.
    """
    if not search_term:
        search_term = random.choice(NASA_SEARCH_TERMS)
    
    api_url = "https://images-api.nasa.gov/search"
    
    params = {
        "q": search_term,
        "media_type": "image",
        "page_size": 50,  # Get more results for better random selection
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        items = data.get("collection", {}).get("items", [])
        
        if not items:
            print(f"No NASA images found for: {search_term}")
            return None
        
        # Pick a random image from results
        item = random.choice(items)
        item_data = item.get("data", [{}])[0]
        links = item.get("links", [])
        
        # Find the image URL (prefer medium/large size)
        image_url = None
        for link in links:
            if link.get("rel") == "preview":
                image_url = link.get("href", "")
                break
        
        if not image_url and links:
            image_url = links[0].get("href", "")
        
        return {
            "title": item_data.get("title", "NASA Image"),
            "description": item_data.get("description", ""),
            "url": image_url,
            "date": item_data.get("date_created", ""),
            "center": item_data.get("center", "NASA"),
            "search_term": search_term,
        }
    
    except requests.RequestException as e:
        print(f"NASA Image Library API error: {e}")
        return None


def get_apod_for_episode() -> Optional[dict]:
    """Get NASA image for episode metadata.
    
    Tries APOD first, falls back to NASA Image Library if APOD is a video.
    
    Returns:
        Dictionary with episode-relevant fields, or None.
        {
            "image_url": "URL to use as episode artwork",
            "image_title": "Title for alt text/credits",
            "image_credit": "Copyright holder",
            "source": "apod" or "nasa_library"
        }
    """
    # Try APOD first
    apod = fetch_apod()
    
    if apod and apod.get("media_type") == "image":
        return {
            "image_url": apod.get("url") or apod.get("hdurl"),
            "image_title": apod.get("title", "NASA APOD"),
            "image_credit": apod.get("copyright", "NASA"),
            "source": "apod",
        }
    
    # Fallback to NASA Image Library
    print("APOD is video/unavailable, trying NASA Image Library...")
    nasa_image = fetch_nasa_image_library()
    
    if nasa_image and nasa_image.get("url"):
        return {
            "image_url": nasa_image.get("url"),
            "image_title": nasa_image.get("title", "NASA Image"),
            "image_credit": f"NASA/{nasa_image.get('center', 'NASA')}",
            "source": "nasa_library",
        }
    
    return None

