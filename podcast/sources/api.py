"""Generic REST API content source for future expansion."""

import os
import re
import requests
from datetime import datetime
from typing import Any, Optional

from .base import BaseSource, ContentItem


class APISource(BaseSource):
    """Generic REST API content source.
    
    This source allows fetching content from any REST API by
    configuring the endpoint, headers, and response field mapping.
    
    Example config:
        name: "Example API"
        enabled: true
        url: "https://api.example.com/articles"
        method: "GET"
        headers:
          Authorization: "Bearer ${API_KEY}"
        params:
          category: "positive"
          limit: 10
        response_path: "data.articles"  # JSONPath to items array
        mapping:
          title: "headline"
          summary: "description"
          url: "link"
          published: "publishedAt"
        tags: ["custom"]
    """
    
    def __init__(self, config: dict):
        """Initialize API source with configuration."""
        super().__init__(config)
        self.url = config.get("url", "")
        self.method = config.get("method", "GET").upper()
        self.headers = config.get("headers", {})
        self.params = config.get("params", {})
        self.response_path = config.get("response_path", "")
        self.mapping = config.get("mapping", {})
        self.tags = config.get("tags", [])
        self.max_items = config.get("max_items", 10)
    
    def fetch(self) -> list[ContentItem]:
        """Fetch content items from the API.
        
        Returns:
            List of ContentItem objects.
        """
        if not self.enabled or not self.url:
            return []
        
        try:
            # Interpolate environment variables in headers
            headers = self._interpolate_env_vars(self.headers)
            
            # Make the request
            if self.method == "GET":
                response = requests.get(
                    self.url,
                    headers=headers,
                    params=self.params,
                    timeout=15,
                )
            elif self.method == "POST":
                response = requests.post(
                    self.url,
                    headers=headers,
                    json=self.params,
                    timeout=15,
                )
            else:
                print(f"Unsupported HTTP method: {self.method}")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # Extract items array from response
            items_data = self._extract_path(data, self.response_path)
            
            if not isinstance(items_data, list):
                print(f"Response path did not yield a list: {self.response_path}")
                return []
            
            # Map to ContentItems
            items = []
            for item_data in items_data[:self.max_items]:
                item = self._map_to_content_item(item_data)
                if item:
                    items.append(item)
            
            return items
        
        except requests.RequestException as e:
            print(f"API request error for {self.name}: {e}")
            return []
        except Exception as e:
            print(f"Error processing API response from {self.name}: {e}")
            return []
    
    def _interpolate_env_vars(self, data: dict) -> dict:
        """Replace ${VAR_NAME} patterns with environment variable values."""
        result = {}
        pattern = re.compile(r'\$\{([^}]+)\}')
        
        for key, value in data.items():
            if isinstance(value, str):
                def replace_var(match):
                    var_name = match.group(1)
                    return os.environ.get(var_name, match.group(0))
                
                result[key] = pattern.sub(replace_var, value)
            else:
                result[key] = value
        
        return result
    
    def _extract_path(self, data: Any, path: str) -> Any:
        """Extract nested value from data using dot notation path.
        
        Example: "data.articles" extracts data["data"]["articles"]
        """
        if not path:
            return data
        
        parts = path.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                current = current[index] if index < len(current) else None
            else:
                return None
            
            if current is None:
                return None
        
        return current
    
    def _map_to_content_item(self, data: dict) -> Optional[ContentItem]:
        """Map API response item to ContentItem using configured mapping."""
        # Get mapped fields
        title = self._get_mapped_value(data, "title")
        url = self._get_mapped_value(data, "url")
        
        if not title or not url:
            return None
        
        summary = self._get_mapped_value(data, "summary") or ""
        published_str = self._get_mapped_value(data, "published")
        
        # Parse published date
        published = None
        if published_str:
            try:
                published = datetime.fromisoformat(
                    published_str.replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                pass
        
        return ContentItem(
            title=title,
            url=url,
            source=self.name,
            summary=summary,
            published=published,
            tags=self.tags.copy(),
        )
    
    def _get_mapped_value(self, data: dict, field: str) -> Optional[str]:
        """Get value from data using field mapping.
        
        If mapping exists for field, use mapped key; otherwise use field directly.
        """
        key = self.mapping.get(field, field)
        value = self._extract_path(data, key)
        return str(value) if value is not None else None


def fetch_all_api_sources(sources_config: list[dict]) -> list[ContentItem]:
    """Fetch items from all configured API sources.
    
    Args:
        sources_config: List of API source configurations.
    
    Returns:
        Combined list of ContentItem objects from all sources.
    """
    all_items = []
    
    for source_config in sources_config:
        source = APISource(source_config)
        if source.is_enabled():
            items = source.fetch()
            all_items.extend(items)
            print(f"Fetched {len(items)} items from API: {source.name}")
    
    return all_items

