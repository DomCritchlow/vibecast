"""Generate the site pages from Jinja2 templates."""

import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape


def get_template_env() -> Environment:
    """Create and return the Jinja2 environment."""
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    return env


def get_base_url(feed_url: str) -> str:
    """Extract the base website URL from an RSS feed URL."""
    try:
        parsed = urlparse(feed_url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return feed_url


def get_template_context(config: dict) -> dict:
    """Build the template context from config.
    
    Args:
        config: Full configuration dictionary.
    
    Returns:
        Dictionary of template variables.
    """
    podcast = config.get("podcast", {})
    vibe = config.get("vibe", {})
    episode_config = config.get("episode", {})
    storage = config.get("storage", {})
    r2_config = storage.get("r2", {})
    sources_config = config.get("sources", {})
    tts_root_config = config.get("tts", {})
    
    # Extract values with defaults
    title = podcast.get("title", "Vibecast")
    short_title = title.split(":")[0].strip() if ":" in title else title
    tagline = podcast.get("tagline", "A daily podcast of good news and good vibes.")
    author = podcast.get("author", "")
    author_url = podcast.get("author_url", "")
    github_url = podcast.get("github_url") or config.get("github_url", "https://github.com/domcritchlow/vibecast")
    
    # Vibe-specific
    mood = vibe.get("mood", {})
    mood_primary = mood.get("primary", "uplifting")
    mood_secondary = mood.get("secondary", "optimistic")
    voice_persona = vibe.get("voice_persona", {})
    persona_name = voice_persona.get("name", "Your daily companion")
    personality_traits = voice_persona.get("personality", [])
    embrace = vibe.get("embrace", {})
    embrace_topics = embrace.get("topics", [])
    avoid_topics = vibe.get("avoid", {}).get("topics", [])
    
    # Episode details
    target_minutes = episode_config.get("target_minutes", 4)
    
    # TTS voice - check provider and get from the right place
    tts_provider = tts_root_config.get("provider", "openai")
    if tts_provider == "openai":
        openai_tts = tts_root_config.get("openai", {})
        tts_voice = openai_tts.get("voice", "nova")
    else:  # elevenlabs
        elevenlabs_tts = tts_root_config.get("elevenlabs", {})
        tts_voice = elevenlabs_tts.get("voice_id", "rachel")
    
    # Get enabled RSS sources with their URLs
    rss_sources = sources_config.get("rss", [])
    enabled_sources = [s for s in rss_sources if s.get("enabled", True)]
    
    # Extract source info (name and base URL)
    source_info = [
        {"name": s.get("name", "Unknown"), "url": get_base_url(s.get("url", ""))}
        for s in enabled_sources
    ]
    
    # R2 public URL for transcripts (from env or config)
    r2_public_url = os.environ.get("VIBECAST_R2_PUBLIC_URL", r2_config.get("public_base_url", ""))
    
    # Voice descriptions (OpenAI TTS voices)
    voice_descriptions = {
        "alloy": "balanced & versatile",
        "ash": "expressive & dynamic",
        "ballad": "smooth & expressive",
        "cedar": "clear & natural",
        "coral": "warm & friendly",
        "echo": "warm & conversational",
        "fable": "expressive storyteller",
        "marin": "clear & professional",
        "nova": "friendly & warm",
        "onyx": "deep & authoritative",
        "sage": "clear & balanced",
        "shimmer": "soft & gentle",
        "verse": "natural & engaging",
    }
    voice_desc = voice_descriptions.get(tts_voice, "AI-narrated")
    
    # Build embrace topics for features (pick first 3)
    topics_text = ", ".join(embrace_topics[:3]) if embrace_topics else "positive stories"
    
    return {
        "title": title,
        "short_title": short_title,
        "tagline": tagline,
        "author": author,
        "author_url": author_url,
        "github_url": github_url,
        "mood_primary": mood_primary,
        "mood_secondary": mood_secondary,
        "persona_name": persona_name,
        "personality_traits": personality_traits,
        "embrace_topics": embrace_topics,
        "avoid_topics": avoid_topics,
        "target_minutes": target_minutes,
        "tts_provider": tts_provider,
        "tts_voice": tts_voice,
        "voice_desc": voice_desc,
        "topics_text": topics_text,
        "source_info": source_info,
        "r2_public_url": r2_public_url,
        "current_year": datetime.now().year,
    }


def ensure_asset_dirs(site_dir: Path) -> None:
    """Ensure asset directories exist.
    
    Args:
        site_dir: Path to the site directory (docs/).
    """
    assets_dir = site_dir / "assets"
    (assets_dir / "css").mkdir(parents=True, exist_ok=True)
    (assets_dir / "textures").mkdir(parents=True, exist_ok=True)
    (assets_dir / "images").mkdir(parents=True, exist_ok=True)


def get_latest_newspaper_url(site_dir: Path) -> str:
    """Get the latest newspaper PDF URL from the RSS feed.
    
    Args:
        site_dir: Path to the site directory.
    
    Returns:
        URL to latest newspaper PDF or empty string.
    """
    import xml.etree.ElementTree as ET
    
    feed_path = site_dir / "feed.xml"
    if not feed_path.exists():
        return ""
    
    try:
        tree = ET.parse(feed_path)
        root = tree.getroot()
        
        # Find first item (latest episode)
        items = root.findall(".//item")
        if not items:
            return ""
        
        latest_item = items[0]
        
        # Look for newspaper URL in description
        description = latest_item.find("description")
        if description is not None and description.text:
            # Extract newspaper URL from description if it contains 📰 READ:
            import re
            match = re.search(r'📰 READ: (https?://[^\s]+)', description.text)
            if match:
                return match.group(1)
        
        return ""
    except Exception as e:
        print(f"Warning: Could not parse feed for newspaper URL: {e}")
        return ""


def save_site_pages(config: dict, site_dir: Path) -> None:
    """Generate and save all HTML pages to the site directory.
    
    Args:
        config: Full configuration dictionary.
        site_dir: Path to the site directory.
    """
    env = get_template_env()
    context = get_template_context(config)
    
    # Add latest newspaper URL to context
    context["latest_newspaper_url"] = get_latest_newspaper_url(site_dir)
    
    # Ensure asset directories exist
    ensure_asset_dirs(site_dir)
    
    # Render and save each page
    pages = ["index.html", "about.html", "docs.html"]
    for page in pages:
        template = env.get_template(page)
        html = template.render(**context)
        output_path = site_dir / page
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)


# Legacy function name for backward compatibility
def save_index_html(config: dict, site_dir: Path) -> None:
    """Generate and save all HTML pages (legacy function name).
    
    Args:
        config: Full configuration dictionary.
        site_dir: Path to the site directory.
    """
    save_site_pages(config, site_dir)
