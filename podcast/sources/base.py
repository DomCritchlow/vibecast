"""Base classes and data structures for content sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ContentItem:
    """A single content item from any source."""
    
    title: str
    url: str
    source: str
    summary: str = ""
    published: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)
    score: float = 0.0  # Computed relevance score
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "summary": self.summary,
            "published": self.published.isoformat() if self.published else None,
            "tags": self.tags,
            "score": self.score,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ContentItem":
        """Create ContentItem from dictionary."""
        published = None
        if data.get("published"):
            published = datetime.fromisoformat(data["published"])
        
        return cls(
            title=data["title"],
            url=data["url"],
            source=data["source"],
            summary=data.get("summary", ""),
            published=published,
            tags=data.get("tags", []),
            score=data.get("score", 0.0),
        )


class BaseSource(ABC):
    """Abstract base class for content sources."""
    
    def __init__(self, config: dict):
        """Initialize the source with configuration."""
        self.config = config
        self.name = config.get("name", "Unknown Source")
        self.enabled = config.get("enabled", True)
    
    @abstractmethod
    def fetch(self) -> list[ContentItem]:
        """Fetch content items from the source.
        
        Returns:
            List of ContentItem objects.
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if this source is enabled."""
        return self.enabled


def filter_items(
    items: list[ContentItem],
    block_keywords: list[str],
    boost_keywords: list[str],
    used_urls: set[str],
) -> list[ContentItem]:
    """Filter and score content items.
    
    Args:
        items: List of content items to filter.
        block_keywords: Keywords that disqualify an item.
        boost_keywords: Keywords that increase an item's score.
        used_urls: Set of URLs already used (for deduplication).
    
    Returns:
        Filtered and scored list of content items.
    """
    filtered = []
    
    for item in items:
        # Skip if already used
        if item.url in used_urls:
            continue
        
        # Check for block keywords in title and summary
        text = f"{item.title} {item.summary}".lower()
        
        blocked = False
        for keyword in block_keywords:
            if keyword.lower() in text:
                blocked = True
                break
        
        if blocked:
            continue
        
        # Calculate score based on boost keywords
        score = 0.0
        for keyword in boost_keywords:
            if keyword.lower() in text:
                score += 1.0
        
        item.score = score
        filtered.append(item)
    
    # Sort by score (highest first)
    filtered.sort(key=lambda x: x.score, reverse=True)
    
    return filtered


def select_items(
    items: list[ContentItem],
    max_items: int,
    max_per_source: int,
) -> list[ContentItem]:
    """Select final items ensuring source diversity.
    
    Args:
        items: Pre-filtered and scored items.
        max_items: Maximum total items to select.
        max_per_source: Maximum items per source.
    
    Returns:
        Selected list of content items.
    """
    selected = []
    source_counts: dict[str, int] = {}
    
    for item in items:
        if len(selected) >= max_items:
            break
        
        # Check source limit
        current_count = source_counts.get(item.source, 0)
        if current_count >= max_per_source:
            continue
        
        selected.append(item)
        source_counts[item.source] = current_count + 1
    
    return selected

