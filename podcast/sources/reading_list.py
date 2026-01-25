"""Reading list source - for long-form content to recommend, not summarize."""

from .base import ContentItem
from .rss import RSSSource


class ReadingListItem(ContentItem):
    """Extended ContentItem with author and description for reading list."""
    
    def __init__(self, *args, author: str = "", description: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self.author = author
        self.description = description


def fetch_reading_list(config: dict, used_urls: set[str] = None) -> list[ReadingListItem]:
    """Fetch reading list items from configured sources.
    
    Args:
        config: Full configuration dictionary.
        used_urls: Set of URLs that have been used recently (for deduplication).
    
    Returns:
        List of ReadingListItem objects.
    """
    if used_urls is None:
        used_urls = set()
    
    sources_config = config.get("sources", {})
    reading_list_config = sources_config.get("reading_list", {})
    
    if not reading_list_config:
        return []
    
    sources = reading_list_config.get("sources", [])
    max_items = reading_list_config.get("max_items", 3)
    
    all_items = []
    
    for source_config in sources:
        if not source_config.get("enabled", True):
            continue
        
        # Use RSS source to fetch the feed
        rss_source = RSSSource({
            "name": source_config.get("name"),
            "url": source_config.get("url"),
            "enabled": True,
            "max_items": 5,  # Fetch a few recent items
            "tags": source_config.get("tags", []),
        })
        
        items = rss_source.fetch()
        
        # Convert to ReadingListItem with author and description
        # Filter out items that have been used recently
        for item in items:
            if item.url in used_urls:
                continue
                
            reading_item = ReadingListItem(
                title=item.title,
                url=item.url,
                source=item.source,
                summary=item.summary,
                published=item.published,
                tags=item.tags,
                score=item.score,
                author=source_config.get("author", ""),
                description=source_config.get("description", ""),
            )
            all_items.append(reading_item)
        
        if items:
            filtered_count = len([i for i in items if i.url not in used_urls])
            print(f"  Fetched {len(items)} reading list items from {source_config.get('name')} ({filtered_count} new)")
    
    # Sort by published date (most recent first)
    all_items.sort(key=lambda x: x.published or "", reverse=True)
    
    # Limit to max_items
    return all_items[:max_items]
