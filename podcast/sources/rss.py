"""RSS feed fetching and parsing."""

import feedparser
from datetime import datetime
from typing import Optional
from email.utils import parsedate_to_datetime

from .base import BaseSource, ContentItem


class RSSSource(BaseSource):
    """RSS feed content source."""
    
    def __init__(self, config: dict):
        """Initialize RSS source with configuration.
        
        Config should include:
            - name: Source name
            - url: RSS feed URL
            - enabled: Whether source is active
            - max_items: Maximum items to fetch
            - trust_score: Quality score (0.0-1.0)
            - tags: List of category tags
        """
        super().__init__(config)
        self.url = config.get("url", "")
        self.max_items = config.get("max_items", 5)
        self.trust_score = config.get("trust_score", 0.5)
        self.tags = config.get("tags", [])
    
    def fetch(self) -> list[ContentItem]:
        """Fetch and parse RSS feed.
        
        Returns:
            List of ContentItem objects from the feed.
        """
        if not self.enabled or not self.url:
            return []
        
        try:
            feed = feedparser.parse(self.url)
            
            if feed.bozo and not feed.entries:
                print(f"RSS parse error for {self.name}: {feed.bozo_exception}")
                return []
            
            items = []
            for entry in feed.entries[:self.max_items]:
                item = self._parse_entry(entry)
                if item:
                    items.append(item)
            
            return items
        
        except Exception as e:
            print(f"Error fetching RSS from {self.name}: {e}")
            return []
    
    def _parse_entry(self, entry) -> Optional[ContentItem]:
        """Parse a single RSS entry into a ContentItem."""
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        
        if not title or not link:
            return None
        
        # Get summary/description
        summary = ""
        if entry.get("summary"):
            summary = entry.summary
        elif entry.get("description"):
            summary = entry.description
        
        # Clean HTML from summary
        summary = self._clean_html(summary)
        
        # Truncate summary if too long (keep more context for richer scripts)
        if len(summary) > 1000:
            summary = summary[:997] + "..."
        
        # Parse published date
        published = None
        if entry.get("published"):
            published = self._parse_date(entry.published)
        elif entry.get("updated"):
            published = self._parse_date(entry.updated)
        
        return ContentItem(
            title=title,
            url=link,
            source=self.name,
            summary=summary,
            published=published,
            tags=self.tags.copy(),
            score=self.trust_score,  # Initial score from trust
        )
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        import re
        
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        
        # Decode common HTML entities
        clean = clean.replace('&amp;', '&')
        clean = clean.replace('&lt;', '<')
        clean = clean.replace('&gt;', '>')
        clean = clean.replace('&quot;', '"')
        clean = clean.replace('&#39;', "'")
        clean = clean.replace('&nbsp;', ' ')
        
        # Normalize whitespace
        clean = ' '.join(clean.split())
        
        return clean.strip()
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats from RSS feeds."""
        if not date_str:
            return None
        
        # Try RFC 2822 format (common in RSS)
        try:
            return parsedate_to_datetime(date_str)
        except (TypeError, ValueError):
            pass
        
        # Try ISO format
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        # Try common formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d %b %Y %H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str[:len(fmt) + 5], fmt)
            except ValueError:
                continue
        
        return None


def fetch_rss_items(url: str, source_name: str = "RSS") -> list[ContentItem]:
    """Convenience function to fetch items from a single RSS URL.
    
    Args:
        url: RSS feed URL.
        source_name: Name to assign to the source.
    
    Returns:
        List of ContentItem objects.
    """
    config = {
        "name": source_name,
        "url": url,
        "enabled": True,
        "max_items": 10,
    }
    source = RSSSource(config)
    return source.fetch()


def fetch_all_rss_sources(sources_config: list[dict]) -> list[ContentItem]:
    """Fetch items from all configured RSS sources.
    
    Args:
        sources_config: List of RSS source configurations.
    
    Returns:
        Combined list of ContentItem objects from all sources.
    """
    all_items = []
    
    for source_config in sources_config:
        source = RSSSource(source_config)
        if source.is_enabled():
            items = source.fetch()
            all_items.extend(items)
            print(f"Fetched {len(items)} items from {source.name}")
    
    return all_items

