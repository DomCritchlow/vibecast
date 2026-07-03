"""RSS feed fetching and parsing.

Feeds are downloaded concurrently with httpx (explicit timeouts, one retry)
and parsed with feedparser. A single slow or hung feed can no longer stall
the whole daily run.
"""

import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from .base import BaseSource, ContentItem

logger = logging.getLogger(__name__)

FETCH_TIMEOUT_SECONDS = 15.0
MAX_CONCURRENT_FETCHES = 8
USER_AGENT = "Vibecast/2.0 (+https://github.com/domcritchlow/vibecast)"


def _download_feed(url: str) -> bytes:
    """Download raw feed bytes with a timeout and one retry."""
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = httpx.get(
                url,
                timeout=FETCH_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as e:
            last_error = e
            if attempt == 0:
                logger.debug("Retrying %s after error: %s", url, e)
    raise last_error  # type: ignore[misc]


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
        """Fetch and parse the RSS feed.

        Returns:
            List of ContentItem objects from the feed.
        """
        if not self.enabled or not self.url:
            return []

        try:
            raw = _download_feed(self.url)
        except Exception as e:
            logger.warning("Failed to download RSS feed %s (%s): %s", self.name, self.url, e)
            return []

        feed = feedparser.parse(raw)

        if feed.bozo and not feed.entries:
            logger.warning("RSS parse error for %s: %s", self.name, feed.bozo_exception)
            return []

        items = []
        # Fetch more items than we need so scoring can find the best ones.
        # The global selection step will limit to max_items per source.
        fetch_limit = max(self.max_items * 5, 10)
        for entry in feed.entries[:fetch_limit]:
            item = self._parse_entry(entry)
            if item:
                items.append(item)

        return items

    def _parse_entry(self, entry) -> ContentItem | None:
        """Parse a single RSS entry into a ContentItem."""
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()

        if not title or not link:
            return None

        summary = entry.get("summary") or entry.get("description") or ""
        summary = clean_html(summary)

        # Truncate summary if too long (keep more context for richer scripts)
        if len(summary) > 1000:
            summary = summary[:997] + "..."

        published = None
        if entry.get("published"):
            published = parse_feed_date(entry.published)
        elif entry.get("updated"):
            published = parse_feed_date(entry.updated)

        return ContentItem(
            title=clean_html(title),
            url=link,
            source=self.name,
            summary=summary,
            published=published,
            tags=self.tags.copy(),
            score=self.trust_score,  # Initial score from trust
        )


def clean_html(text: str) -> str:
    """Strip HTML tags and decode all entities (named and numeric)."""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = html.unescape(clean)
    clean = clean.replace("\xa0", " ")
    return " ".join(clean.split()).strip()


def parse_feed_date(date_str: str) -> datetime | None:
    """Parse various date formats found in RSS feeds."""
    if not date_str:
        return None

    # RFC 2822 (the common RSS format)
    try:
        return parsedate_to_datetime(date_str)
    except (TypeError, ValueError):
        pass

    # ISO 8601
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        pass

    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d %b %Y %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str[: len(fmt) + 5], fmt)
        except ValueError:
            continue

    return None


def fetch_rss_items(url: str, source_name: str = "RSS") -> list[ContentItem]:
    """Convenience function to fetch items from a single RSS URL."""
    source = RSSSource({"name": source_name, "url": url, "enabled": True, "max_items": 10})
    return source.fetch()


def fetch_all_rss_sources(sources_config: list[dict]) -> list[ContentItem]:
    """Fetch items from all configured RSS sources concurrently.

    Args:
        sources_config: List of RSS source configurations.

    Returns:
        Combined list of ContentItem objects, in config order.
    """
    sources = [RSSSource(cfg) for cfg in sources_config]
    sources = [s for s in sources if s.is_enabled()]
    if not sources:
        return []

    results: dict[str, list[ContentItem]] = {}
    with ThreadPoolExecutor(max_workers=min(MAX_CONCURRENT_FETCHES, len(sources))) as pool:
        futures = {pool.submit(source.fetch): source for source in sources}
        for future in as_completed(futures):
            source = futures[future]
            items = future.result()  # fetch() never raises; errors return []
            results[source.name] = items
            logger.info("Fetched %d items from %s", len(items), source.name)

    # Preserve config order for deterministic downstream selection
    all_items: list[ContentItem] = []
    for source in sources:
        all_items.extend(results.get(source.name, []))
    return all_items
