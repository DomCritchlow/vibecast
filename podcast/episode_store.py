"""Episode metadata store - utilities for reading/writing episode JSON files."""

import json
import logging
from pathlib import Path

from .models import Episode

logger = logging.getLogger(__name__)

EPISODES_DIR = Path(__file__).parent / "episodes"


def load_episode(episode_id: str) -> dict | None:
    """Load a single episode's metadata.

    Args:
        episode_id: Episode ID (e.g., "2026-01-25")

    Returns:
        Episode metadata dict or None if not found.
    """
    json_path = EPISODES_DIR / f"{episode_id}.json"

    if not json_path.exists():
        return None

    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def save_episode(episode_data: dict) -> Path:
    """Save episode metadata to JSON file.

    Args:
        episode_data: Episode metadata dict (must have 'guid' field)

    Returns:
        Path to saved JSON file.

    Raises:
        pydantic.ValidationError: If the episode data is malformed.
    """
    EPISODES_DIR.mkdir(parents=True, exist_ok=True)

    # Validate against the Episode schema before writing — these files are
    # the source of truth for the feed and site.
    Episode.model_validate(episode_data)

    episode_id = episode_data["guid"]
    json_path = EPISODES_DIR / f"{episode_id}.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(episode_data, f, indent=2, ensure_ascii=False)

    return json_path


def load_all_episodes(limit: int | None = None, reverse: bool = True) -> list[dict]:
    """Load all episodes, sorted by date.

    Args:
        limit: Maximum number of episodes to return (None = all)
        reverse: If True, newest first; if False, oldest first

    Returns:
        List of episode metadata dicts.
    """
    EPISODES_DIR.mkdir(parents=True, exist_ok=True)

    episodes = []

    for json_path in EPISODES_DIR.glob("*.json"):
        if json_path.name == ".gitkeep":
            continue

        try:
            with open(json_path, encoding="utf-8") as f:
                episode = json.load(f)
                episodes.append(episode)
        except Exception as e:
            logger.warning("Could not load %s: %s", json_path, e)

    # Sort by date
    episodes.sort(key=lambda e: e["date"], reverse=reverse)

    # Apply limit
    if limit:
        episodes = episodes[:limit]

    return episodes


def episode_exists(episode_id: str) -> bool:
    """Check if an episode exists.

    Args:
        episode_id: Episode ID (e.g., "2026-01-25")

    Returns:
        True if episode JSON file exists.
    """
    json_path = EPISODES_DIR / f"{episode_id}.json"
    return json_path.exists()


def get_latest_episode() -> dict | None:
    """Get the most recent episode.

    Returns:
        Episode metadata dict or None if no episodes exist.
    """
    episodes = load_all_episodes(limit=1, reverse=True)
    return episodes[0] if episodes else None


def count_episodes() -> int:
    """Count total number of episodes.

    Returns:
        Number of episode JSON files.
    """
    EPISODES_DIR.mkdir(parents=True, exist_ok=True)
    return len(list(EPISODES_DIR.glob("*.json")))


def search_episodes(query: str, field: str = "title") -> list[dict]:
    """Search episodes by field content.

    Args:
        query: Search query (case-insensitive)
        field: Field to search in (default: "title")

    Returns:
        List of matching episode metadata dicts.
    """
    query_lower = query.lower()
    episodes = load_all_episodes()

    results = []
    for episode in episodes:
        field_value = episode.get(field, "")
        if isinstance(field_value, str) and query_lower in field_value.lower():
            results.append(episode)

    return results


def get_episodes_by_date_range(start_date: str, end_date: str) -> list[dict]:
    """Get episodes within a date range.

    Args:
        start_date: Start date (ISO format: "2026-01-01")
        end_date: End date (ISO format: "2026-01-31")

    Returns:
        List of episode metadata dicts within range.
    """
    episodes = load_all_episodes()

    results = []
    for episode in episodes:
        episode_date = episode["date"][:10]  # Get YYYY-MM-DD part
        if start_date <= episode_date <= end_date:
            results.append(episode)

    return results
