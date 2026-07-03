"""Reading list source - for long-form content to recommend, not summarize."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from .base import ContentItem
from .rss import RSSSource

logger = logging.getLogger(__name__)

# Sort fallback for items with no published date (sorts last, newest-first)
_EPOCH = datetime.fromtimestamp(0, tz=UTC)


@dataclass
class ReadingListItem(ContentItem):
    """Extended ContentItem with author and description for reading list."""

    author: str = ""
    description: str = ""


def _sort_key(item: ReadingListItem) -> datetime:
    published = item.published
    if published is None:
        return _EPOCH
    if published.tzinfo is None:
        return published.replace(tzinfo=UTC)
    return published


def fetch_reading_list(config: dict, used_urls: set[str] | None = None) -> list[ReadingListItem]:
    """Fetch reading list items from configured sources.

    Args:
        config: Full configuration dictionary.
        used_urls: Set of URLs that have been used recently (for deduplication).

    Returns:
        List of ReadingListItem objects.
    """
    if used_urls is None:
        used_urls = set()

    reading_list_config = config.get("sources", {}).get("reading_list", {})
    if not reading_list_config:
        return []

    sources = reading_list_config.get("sources", [])
    max_items = reading_list_config.get("max_items", 3)

    all_items: list[ReadingListItem] = []

    for source_config in sources:
        if not source_config.get("enabled", True):
            continue

        rss_source = RSSSource(
            {
                "name": source_config.get("name"),
                "url": source_config.get("url"),
                "enabled": True,
                "max_items": 5,  # Fetch a few recent items
                "tags": source_config.get("tags", []),
            }
        )

        items = rss_source.fetch()

        new_items = [
            ReadingListItem(
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
            for item in items
            if item.url not in used_urls
        ]
        all_items.extend(new_items)

        if items:
            logger.info(
                "Fetched %d reading list items from %s (%d new)",
                len(items),
                source_config.get("name"),
                len(new_items),
            )

    # Sort by published date (most recent first); undated items sort last
    all_items.sort(key=_sort_key, reverse=True)

    return all_items[:max_items]
