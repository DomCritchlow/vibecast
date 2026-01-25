"""Generate newspaper-style PDF from episode data."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader


def generate_newspaper_pdf(
    date: datetime,
    items: list,
    config: dict,
    weather_text: str = "",
    reading_items: list = None,
    duration_minutes: float = 5.0,
    output_path: Optional[Path] = None,
    episode_artwork_url: str = None,
    accent_color: str = None,
    max_stories: int = 6,
    max_reading_items: int = 3,
) -> Path:
    """Generate a newspaper-style PDF for the episode.
    
    Args:
        date: Episode date.
        items: List of ContentItem objects.
        config: Full configuration dictionary.
        weather_text: Weather description.
        reading_items: List of reading list items.
        duration_minutes: Episode duration in minutes.
        output_path: Optional custom output path.
        episode_artwork_url: URL to episode artwork image.
        accent_color: Hex color for accents (from artwork palette).
        max_stories: Maximum number of stories to include (default: 6, ensures one-page fit).
        max_reading_items: Maximum number of reading list items (default: 3, ensures one-page fit).
    
    Returns:
        Path to the generated PDF file.
    """
    try:
        from weasyprint import HTML
    except ImportError:
        print("Warning: WeasyPrint not installed. Run: pip install weasyprint")
        print("Skipping newspaper PDF generation.")
        return None
    
    # Setup Jinja2 environment
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("newspaper.html")
    
    # Get config values
    podcast = config.get("podcast", {})
    vibe = config.get("vibe", {})
    
    # Prepare data for template
    lead_story = items[0] if items else None
    other_stories = items[1:] if len(items) > 1 else []
    
    # Warn if content will be truncated to fit one page
    if len(other_stories) > max_stories:
        print(f"⚠️  Warning: {len(other_stories)} stories available, but only {max_stories} will fit on one page.")
        print(f"   Showing first {max_stories} stories to ensure single-page layout.")
    
    # Limit stories to ensure one-page fit
    other_stories = other_stories[:max_stories]
    
    # Truncate summaries for print (conservative limits for one-page guarantee)
    if lead_story:
        lead_story = {
            "title": lead_story.title,
            "summary": _truncate(lead_story.summary, 250),  # Reduced from 250 for one-page fit
            "source": lead_story.source,
            "url": lead_story.url,
        }
    
    stories = []
    for story in other_stories:
        stories.append({
            "title": story.title,
            "summary": _truncate(story.summary, 150),  # Reduced from 150 for one-page fit
            "source": story.source,
            "url": story.url,
        })
    
    # Format reading list items (strict limit for one-page fit)
    reading_list = []
    if reading_items:
        # Warn if reading list will be truncated
        if len(reading_items) > max_reading_items:
            print(f"⚠️  Warning: {len(reading_items)} reading items available, but only {max_reading_items} will fit on one page.")
            print(f"   Showing first {max_reading_items} items to ensure single-page layout.")
        
        # Limit number of reading items
        limited_reading = reading_items[:max_reading_items]
        for item in limited_reading:
            # Get author and description
            author = getattr(item, 'author', '')
            description = getattr(item, 'description', '')
            
            # If no description, use truncated summary
            if not description and hasattr(item, 'summary'):
                description = _truncate(item.summary, 100)  # Conservative truncation
            
            reading_list.append({
                "title": item.title,
                "author": author,
                "description": description,
                "url": item.url,
            })
    
    # Calculate issue number (days since Jan 1, 2024)
    epoch = datetime(2026, 1, 1)
    issue_number = (date - epoch).days + 1
    
    # Get accent color from config if not provided
    if not accent_color:
        artwork_config = config.get("artwork", {})
        accent_palette = artwork_config.get("accent_palette", [])
        # Use the first palette color or default
        if accent_palette:
            accent_color = _color_name_to_hex(accent_palette[0])
        else:
            accent_color = "#ff6b35"  # Default burnt orange
    
    # Render HTML
    html_content = template.render(
        title=vibe.get("name", "Morning Thread"),
        tagline=podcast.get("tagline", "Your daily podcast"),
        date=date.strftime("%A, %B %d, %Y"),
        issue_number=issue_number,
        lead_story=lead_story,
        weather=_clean_weather(weather_text),
        stories=stories,
        reading_items=reading_list,
        site_url=_clean_url(podcast.get("site_url", ""), fallback=podcast.get("github_url", "")),
        duration=f"~{duration_minutes:.0f}",
        generation_date=datetime.now().strftime("%H:%M %Z"),
        accent_color=accent_color,
        episode_artwork=episode_artwork_url,
    )
    
    # Determine output path
    if output_path is None:
        # Default: save to docs/newspapers/
        docs_dir = Path(__file__).parent.parent / "docs"
        newspapers_dir = docs_dir / "newspapers"
        newspapers_dir.mkdir(parents=True, exist_ok=True)
        output_path = newspapers_dir / f"{date.strftime('%Y-%m-%d')}.pdf"
    
    # Generate PDF
    print(f"  Generating newspaper PDF...")
    
    # Set base_url to newspapers directory so relative paths (../artwork.png) work correctly
    # The HTML references ../artwork.png which goes up from newspapers/ to docs/
    base_url = f"file://{output_path.parent.absolute()}/"
    
    HTML(string=html_content, base_url=base_url).write_pdf(
        str(output_path),
        stylesheets=None,
        presentational_hints=True,
    )
    
    print(f"  Newspaper saved to: {output_path}")
    
    return output_path


def _truncate(text: str, max_length: int) -> str:
    """Truncate text to max_length, ending at a sentence if possible."""
    if not text or len(text) <= max_length:
        return text
    
    # Try to truncate at a sentence boundary
    truncated = text[:max_length]
    
    # Find last sentence ending
    for punct in ['. ', '! ', '? ']:
        last_sentence = truncated.rfind(punct)
        if last_sentence > max_length * 0.5:  # Don't truncate too aggressively
            return truncated[:last_sentence + 1]
    
    # No sentence boundary found, just truncate
    return truncated[:max_length - 3] + "..."


def _clean_weather(weather_text: str) -> str:
    """Clean weather text for newspaper display."""
    if not weather_text:
        return "Weather information unavailable"
    
    # Truncate to 2 sentences max
    sentences = weather_text.split('. ')
    if len(sentences) > 2:
        return '. '.join(sentences[:2]) + '.'
    
    return weather_text


def _clean_url(url: str, fallback: str = None) -> str:
    """Clean URL for display (remove https://)."""
    if not url:
        # Use fallback or github URL if available
        if fallback:
            url = fallback
        else:
            return "github.com/domcritchlow/vibecast"
    
    return url.replace("https://", "").replace("http://", "").rstrip("/")


def _color_name_to_hex(color_name: str) -> str:
    """Convert color name to hex code."""
    # Color palette mapping
    color_map = {
        "burnt orange": "#ff6b35",
        "deep teal": "#008b8b",
        "electric purple": "#9333ea",
        "muted tan": "#d4a574",
        "sage green": "#9ca986",
        "dusty rose": "#dcae96",
        "federal blue": "#1e3a8a",
        "mint": "#4ade80",
        "sunflower": "#fbbf24",
    }
    
    # Normalize the color name
    normalized = color_name.lower().strip()
    
    # Return hex if found, otherwise return the input (might already be hex)
    if normalized in color_map:
        return color_map[normalized]
    
    # If it's already a hex code, return it
    if normalized.startswith('#'):
        return normalized
    
    # Default fallback
    return "#ff6b35"


def generate_newspaper_html(
    date: datetime,
    items: list,
    config: dict,
    weather_text: str = "",
    reading_items: list = None,
    duration_minutes: float = 5.0,
    output_path: Optional[Path] = None,
    episode_artwork_url: str = None,
    accent_color: str = None,
) -> Path:
    """Generate newspaper HTML (without PDF conversion).
    
    Useful for debugging/previewing the design.
    
    Args:
        date: Episode date.
        items: List of ContentItem objects.
        config: Full configuration dictionary.
        weather_text: Weather description.
        reading_items: List of reading list items.
        duration_minutes: Episode duration in minutes.
        output_path: Optional custom output path.
        episode_artwork_url: URL to episode artwork image.
        accent_color: Hex color for accents (from artwork palette).
    
    Returns:
        Path to the generated HTML file.
    """
    # Setup Jinja2 environment
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("newspaper.html")
    
    # Get config values
    podcast = config.get("podcast", {})
    vibe = config.get("vibe", {})
    
    # Prepare data (same as PDF generation)
    lead_story = items[0] if items else None
    other_stories = items[1:] if len(items) > 1 else []
    
    if lead_story:
        lead_story = {
            "title": lead_story.title,
            "summary": _truncate(lead_story.summary, 250),
            "source": lead_story.source,
            "url": lead_story.url,
        }
    
    stories = []
    for story in other_stories:
        stories.append({
            "title": story.title,
            "summary": _truncate(story.summary, 150),
            "source": story.source,
            "url": story.url,
        })
    
    reading_list = []
    if reading_items:
        for item in reading_items:
            author = getattr(item, 'author', '')
            description = getattr(item, 'description', '')
            
            if not description and hasattr(item, 'summary'):
                description = _truncate(item.summary, 100)
            
            reading_list.append({
                "title": item.title,
                "author": author,
                "description": description,
                "url": item.url,
            })
    
    epoch = datetime(2024, 1, 1)
    issue_number = (date - epoch).days + 1
    
    # Get accent color from config if not provided
    if not accent_color:
        artwork_config = config.get("artwork", {})
        accent_palette = artwork_config.get("accent_palette", [])
        # Use the first palette color or default
        if accent_palette:
            accent_color = _color_name_to_hex(accent_palette[0])
        else:
            accent_color = "#ff6b35"  # Default burnt orange
    
    # Render HTML
    html_content = template.render(
        title=vibe.get("name", "Morning Thread"),
        tagline=podcast.get("tagline", "Your daily podcast"),
        date=date.strftime("%A, %B %d, %Y"),
        issue_number=issue_number,
        lead_story=lead_story,
        weather=_clean_weather(weather_text),
        stories=stories,
        reading_items=reading_list,
        site_url=_clean_url(podcast.get("site_url", ""), fallback=podcast.get("github_url", "")),
        duration=f"~{duration_minutes:.0f}",
        generation_date=datetime.now().strftime("%H:%M %Z"),
        accent_color=accent_color,
        episode_artwork=episode_artwork_url,
    )
    
    # Determine output path
    if output_path is None:
        docs_dir = Path(__file__).parent.parent / "docs"
        newspapers_dir = docs_dir / "newspapers"
        newspapers_dir.mkdir(parents=True, exist_ok=True)
        output_path = newspapers_dir / f"{date.strftime('%Y-%m-%d')}.html"
    
    # Write HTML
    output_path.write_text(html_content, encoding="utf-8")
    print(f"  Newspaper HTML saved to: {output_path}")
    
    return output_path
