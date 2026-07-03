"""RSS feed generation for podcast distribution.

The feed is always regenerated in full from the episode JSON store
(podcast/episodes/*.json) — the single source of truth. feed.xml itself is
a build artifact and is never parsed back.
"""

import html
import logging
import os
from datetime import datetime
from email.utils import format_datetime
from types import SimpleNamespace

logger = logging.getLogger(__name__)


def create_feed_xml(config: dict, episodes: list[dict]) -> str:
    """Create a complete RSS 2.0 podcast feed.

    Args:
        config: Full configuration dictionary.
        episodes: List of episode metadata dictionaries.

    Returns:
        RSS XML string.
    """
    podcast = config.get("podcast", {})
    feed_config = config.get("feed", {})

    # Get values with defaults
    title = _escape(podcast.get("title", "Vibecast"))
    site_url = _escape(podcast.get("site_url", ""))
    feed_url = _escape(podcast.get("feed_url", ""))
    description = _escape(podcast.get("description", ""))
    author = _escape(podcast.get("author", ""))
    language = podcast.get("language", "en-us")
    category = _escape(podcast.get("category", "News"))
    subcategory = _escape(podcast.get("subcategory", ""))
    explicit = podcast.get("explicit", "no")
    artwork_url = _escape(podcast.get("artwork_url", ""))

    # Build channel XML
    channel_parts = [
        f"    <title>{title}</title>",
        f"    <link>{site_url}</link>",
        f"    <description>{description}</description>",
        f"    <language>{language}</language>",
        f"    <lastBuildDate>{format_datetime(datetime.now())}</lastBuildDate>",
    ]

    # Atom self-link (helps with validation)
    if feed_url:
        channel_parts.append(
            f'    <atom:link href="{feed_url}" rel="self" type="application/rss+xml"/>'
        )

    # iTunes required elements
    channel_parts.extend(
        [
            f"    <itunes:author>{author}</itunes:author>",
            f"    <itunes:summary>{description}</itunes:summary>",
            "    <itunes:type>episodic</itunes:type>",
            f"    <itunes:explicit>{explicit}</itunes:explicit>",
        ]
    )

    # Owner (with email for Apple Podcasts)
    owner_email = _escape(podcast.get("owner_email", ""))
    channel_parts.append("    <itunes:owner>")
    channel_parts.append(f"      <itunes:name>{author}</itunes:name>")
    if owner_email:
        channel_parts.append(f"      <itunes:email>{owner_email}</itunes:email>")
    channel_parts.append("    </itunes:owner>")

    # Category
    if subcategory:
        channel_parts.extend(
            [
                f'    <itunes:category text="{category}">',
                f'      <itunes:category text="{subcategory}"/>',
                "    </itunes:category>",
            ]
        )
    else:
        channel_parts.append(f'    <itunes:category text="{category}"/>')

    # Artwork (required for most podcast apps)
    if artwork_url:
        channel_parts.extend(
            [
                "    <image>",
                f"      <url>{artwork_url}</url>",
                f"      <title>{title}</title>",
                f"      <link>{site_url}</link>",
                "    </image>",
                f'    <itunes:image href="{artwork_url}"/>',
            ]
        )

    # Add episodes
    max_episodes = feed_config.get("max_episodes", 30)
    for episode in episodes[:max_episodes]:
        episode_xml = create_episode_item(episode, config)
        channel_parts.append(episode_xml)

    # Build complete RSS feed
    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
{chr(10).join(channel_parts)}
  </channel>
</rss>"""

    return rss_xml


def create_episode_item(episode: dict, config: dict) -> str:
    """Create an RSS item element for an episode.

    Args:
        episode: Episode metadata dictionary.
        config: Full configuration dictionary.

    Returns:
        XML string for the episode item.
    """
    title = _escape(episode.get("title", "Untitled Episode"))
    url = _escape(episode.get("url", ""))
    file_size = episode.get("file_size", 0)
    guid = _escape(episode.get("guid", ""))

    # Format publication date
    pub_date = episode.get("pub_date")
    if isinstance(pub_date, datetime):
        pub_date_str = format_datetime(pub_date)
    elif isinstance(pub_date, str):
        pub_date_str = pub_date
    else:
        pub_date_str = format_datetime(datetime.now())

    # Format duration
    duration_str = ""
    duration = episode.get("duration")
    if duration:
        if isinstance(duration, (int, float)):
            hours, remainder = divmod(int(duration), 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration_str = f"{minutes}:{seconds:02d}"
        else:
            duration_str = str(duration)

    # Build item XML
    item_parts = [
        "    <item>",
        f"      <title>{title}</title>",
        f"      <description><![CDATA[{episode.get('description', '')}]]></description>",
        f"      <pubDate>{pub_date_str}</pubDate>",
        f'      <guid isPermaLink="false">{guid}</guid>',
        f'      <enclosure url="{url}" length="{file_size}" type="audio/mpeg"/>',
        f"      <itunes:summary><![CDATA[{episode.get('description', '')}]]></itunes:summary>",
        "      <itunes:explicit>no</itunes:explicit>",
        "      <itunes:episodeType>full</itunes:episodeType>",
    ]

    if duration_str:
        item_parts.append(f"      <itunes:duration>{duration_str}</itunes:duration>")

    # Episode-specific image (e.g., NASA APOD)
    episode_image = episode.get("image_url", "")
    if episode_image:
        item_parts.append(f'      <itunes:image href="{_escape(episode_image)}"/>')

    item_parts.append("    </item>")

    return "\n".join(item_parts)


def _escape(text: str) -> str:
    """Escape XML special characters."""
    if not text:
        return ""
    return html.escape(str(text), quote=True)


def episode_json_to_rss_metadata(episode: dict, config: dict) -> dict:
    """Convert a stored episode JSON dict into RSS item metadata."""
    items = [SimpleNamespace(**story) for story in episode.get("stories", [])]
    reading_items = [SimpleNamespace(**reading) for reading in episode.get("reading_list", [])]

    date = datetime.fromisoformat(episode["date"].replace("Z", "+00:00"))

    return create_episode_metadata(
        date=date,
        mp3_url=episode["media"]["audio_url"],
        mp3_size=episode["media"].get("audio_size_bytes", 0),
        duration_seconds=episode.get("duration_seconds"),
        config=config,
        items=items,
        episode_image_url=episode["media"].get("artwork_url"),
        custom_title=episode.get("title"),
        reading_items=reading_items,
        newspaper_url=episode["media"].get("newspaper_url"),
    )


def generate_feed_from_store(config: dict) -> str:
    """Regenerate the full RSS feed XML from the episode JSON store."""
    from .episode_store import load_all_episodes

    episodes_rss = []
    for episode in load_all_episodes():
        try:
            episodes_rss.append(episode_json_to_rss_metadata(episode, config))
        except Exception as e:
            logger.warning("Skipping episode %s in feed: %s", episode.get("guid"), e)

    return create_feed_xml(config, episodes_rss)


def save_feed(feed_path: str, xml_content: str) -> None:
    """Save RSS feed to file.

    Args:
        feed_path: Path to save the feed.xml file.
        xml_content: RSS XML string.
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(feed_path), exist_ok=True)

    with open(feed_path, "w", encoding="utf-8") as f:
        f.write(xml_content)


def create_episode_metadata(
    date: datetime,
    mp3_url: str,
    mp3_size: int,
    duration_seconds: float | None,
    config: dict,
    items: list | None = None,
    episode_image_url: str | None = None,
    custom_title: str | None = None,
    reading_items: list | None = None,
    newspaper_url: str | None = None,
) -> dict:
    """Create episode metadata dictionary.

    Args:
        date: Episode date.
        mp3_url: URL to the MP3 file.
        mp3_size: Size of the MP3 file in bytes.
        duration_seconds: Duration in seconds (optional).
        config: Full configuration dictionary.
        items: List of ContentItem objects used in the episode (optional).
        episode_image_url: URL to episode-specific artwork (e.g., NASA APOD).
        custom_title: Custom episode title (overrides default formatting).
        reading_items: List of reading list items (optional).
        newspaper_url: URL to the newspaper PDF for this episode (optional).

    Returns:
        Episode metadata dictionary.
    """
    podcast = config.get("podcast", {})
    feed_config = config.get("feed", {})
    vibe = config.get("vibe", {})

    # Use custom title if provided, otherwise use configured format
    if custom_title:
        title = custom_title
    else:
        title_format = feed_config.get("episode_title_format", "{podcast_title} — {date}")
        podcast_title = vibe.get("name", podcast.get("title", "Vibecast"))
        date_str = date.strftime("%B %d, %Y")  # e.g., "December 13, 2025"

        title = title_format.format(
            podcast_title=podcast_title,
            date=date_str,
        )

    # Create rich description with summary and references
    description = _build_show_notes(
        date, config, items, duration_seconds, reading_items, newspaper_url
    )

    # Create GUID from date
    guid = date.strftime("%Y-%m-%d")

    metadata = {
        "title": title,
        "description": description,
        "pub_date": date,
        "url": mp3_url,
        "file_size": mp3_size,
        "duration": duration_seconds,
        "guid": guid,
    }

    # Add episode image if provided
    if episode_image_url:
        metadata["image_url"] = episode_image_url

    # Add newspaper URL if provided
    if newspaper_url:
        metadata["newspaper_url"] = newspaper_url

    return metadata


def _build_show_notes(
    date: datetime,
    config: dict,
    items: list | None,
    duration_seconds: float | None,
    reading_items: list | None = None,
    newspaper_url: str | None = None,
) -> str:
    """Build rich show notes with summary and references.

    Args:
        date: Episode date.
        config: Full configuration dictionary.
        items: List of ContentItem objects.
        duration_seconds: Duration in seconds.
        reading_items: List of reading list items (optional).
        newspaper_url: URL to the newspaper PDF (optional).

    Returns:
        Formatted show notes string.
    """
    lines = []

    # Add stories section if items provided - start immediately with content
    if items and len(items) > 0:
        lines.append("IN THIS EPISODE:")
        lines.append("")

        for i, item in enumerate(items, 1):
            lines.append(f"{i}. {item.title}")
            lines.append(f"   Source: {item.source}")

        lines.append("")
        lines.append("REFERENCES:")
        lines.append("")

        for i, item in enumerate(items, 1):
            lines.append(f"{i}. {item.title}")
            lines.append(f"   {item.url}")
            lines.append("")

    # Add reading list section if items provided
    if reading_items and len(reading_items) > 0:
        lines.append("READING LIST:")
        lines.append("Articles recommended for further reading")
        lines.append("")

        for i, item in enumerate(reading_items, 1):
            author_info = f" by {item.author}" if hasattr(item, "author") and item.author else ""
            lines.append(f"{i}. {item.title}{author_info}")
            lines.append(f"   {item.url}")
            lines.append("")

    # Add newspaper link at the end if available
    if newspaper_url:
        lines.append("---")
        lines.append(f"📰 Full newspaper edition: {newspaper_url}")

    return "\n".join(lines)
