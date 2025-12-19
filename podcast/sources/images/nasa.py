"""NASA image provider - APOD and Image Library."""

import random
import requests
from typing import Optional

from .base import ImageProvider, ImageResult


# Default search terms for NASA Image Library fallback
DEFAULT_SEARCH_TERMS = [
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


class NasaImageProvider(ImageProvider):
    """Fetch episode images from NASA sources.
    
    Supports two sources:
    - APOD (Astronomy Picture of the Day): Daily curated space image
    - NASA Image Library: Searchable archive of NASA images
    
    Configuration options in config.yaml:
        sources:
          episode_image:
            provider: "nasa"
            nasa:
              prefer: "apod"  # apod, library, or random
              search_terms: ["nebula", "earth"]  # for library searches
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.nasa_config = self.image_config.get("nasa", {})
        self.prefer = self.nasa_config.get("prefer", "apod")
        self.search_terms = self.nasa_config.get("search_terms", DEFAULT_SEARCH_TERMS)
    
    def get_image(self) -> Optional[ImageResult]:
        """Get an image from NASA sources.
        
        Tries APOD first (unless configured otherwise), falls back to Image Library.
        """
        if self.prefer == "library":
            result = self._fetch_library_image()
            if result:
                return result
            return self._fetch_apod()
        elif self.prefer == "random":
            # Randomly choose between APOD and Library
            if random.choice([True, False]):
                result = self._fetch_apod()
                return result if result else self._fetch_library_image()
            else:
                result = self._fetch_library_image()
                return result if result else self._fetch_apod()
        else:  # Default: prefer APOD
            result = self._fetch_apod()
            if result:
                return result
            print("  APOD unavailable, trying NASA Image Library...")
            return self._fetch_library_image()
    
    def _fetch_apod(self) -> Optional[ImageResult]:
        """Fetch today's Astronomy Picture of the Day."""
        api_url = "https://api.nasa.gov/planetary/apod"
        params = {"api_key": "DEMO_KEY"}
        
        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Skip if today's APOD is a video
            if data.get("media_type") != "image":
                print("  Today's APOD is a video, skipping")
                return None
            
            image_url = data.get("url") or data.get("hdurl")
            if not image_url:
                return None
            
            return ImageResult(
                image_url=image_url,
                title=data.get("title", "NASA APOD"),
                credit=data.get("copyright", "NASA"),
                source="nasa_apod"
            )
        
        except requests.RequestException as e:
            print(f"  NASA APOD API error: {e}")
            return None
    
    def _fetch_library_image(self) -> Optional[ImageResult]:
        """Fetch a random image from NASA Image Library."""
        search_term = random.choice(self.search_terms)
        api_url = "https://images-api.nasa.gov/search"
        params = {
            "q": search_term,
            "media_type": "image",
            "page_size": 50,
        }
        
        try:
            response = requests.get(api_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            items = data.get("collection", {}).get("items", [])
            if not items:
                print(f"  No NASA images found for: {search_term}")
                return None
            
            # Pick a random image
            item = random.choice(items)
            item_data = item.get("data", [{}])[0]
            links = item.get("links", [])
            
            # Find preview image URL
            image_url = None
            for link in links:
                if link.get("rel") == "preview":
                    image_url = link.get("href", "")
                    break
            if not image_url and links:
                image_url = links[0].get("href", "")
            
            if not image_url:
                return None
            
            return ImageResult(
                image_url=image_url,
                title=item_data.get("title", "NASA Image"),
                credit=f"NASA/{item_data.get('center', 'NASA')}",
                source="nasa_library"
            )
        
        except requests.RequestException as e:
            print(f"  NASA Image Library API error: {e}")
            return None

