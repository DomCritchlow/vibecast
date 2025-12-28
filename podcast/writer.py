"""Script generation using OpenAI LLM with vibe-aware prompting."""

import random
import re
from datetime import datetime
from openai import OpenAI

from .sources.base import ContentItem


def clean_script_for_tts(script: str) -> str:
    """Remove non-speakable elements from script before TTS.
    
    Args:
        script: Raw script text.
    
    Returns:
        Cleaned script with only speakable text.
    """
    # Remove music cues like [intro music], [outro music], [background music fades]
    script = re.sub(r'\[(?:intro|outro|background)?\s*music[^\]]*\]', '', script, flags=re.IGNORECASE)
    # Remove other stage directions like [fade out], [transition], [cut to]
    script = re.sub(r'\[(?:fade|cut|transition|end|start)[^\]]*\]', '', script, flags=re.IGNORECASE)
    # Convert [pause] markers to ellipsis (which TTS interprets as natural pause)
    script = re.sub(r'\[pause[^\]]*\]', '...', script, flags=re.IGNORECASE)
    # Clean up extra whitespace/newlines left behind
    script = re.sub(r'\n{3,}', '\n\n', script)
    script = re.sub(r'  +', ' ', script)
    return script.strip()


def build_system_prompt(config: dict) -> str:
    """Build the system prompt based on vibe configuration.
    
    Args:
        config: Full configuration dictionary.
    
    Returns:
        System prompt string for the LLM.
    """
    vibe = config.get("vibe", {})
    episode = config.get("episode", {})
    podcast = config.get("podcast", {})
    
    # Extract vibe settings
    mood = vibe.get("mood", {})
    voice_persona = vibe.get("voice_persona", {})
    avoid = vibe.get("avoid", {})
    embrace = vibe.get("embrace", {})
    pacing = episode.get("pacing", {})
    
    # Build personality description
    personality_lines = voice_persona.get("personality", [])
    personality_text = "\n".join(f"- {p}" for p in personality_lines)
    
    # Build avoid/embrace lists
    avoid_emotions = ", ".join(avoid.get("emotions", []))
    avoid_language = ", ".join(avoid.get("language", []))
    embrace_emotions = ", ".join(embrace.get("emotions", []))
    embrace_language = ", ".join(embrace.get("language", []))
    
    # Get script hints
    openai_config = config.get("openai", {})
    script_hints = openai_config.get("script_hints", [])
    hints_text = "\n".join(f"- {h}" for h in script_hints)
    
    # Build the system prompt
    system_prompt = f"""You are {voice_persona.get('name', 'a podcast host')}.

PERSONALITY:
{personality_text}

MOOD: {mood.get('primary', 'calm')}, {mood.get('secondary', 'optimistic')}
ENERGY: {mood.get('energy', 'gentle-lift')}

EMOTIONAL TONE:
- EMBRACE these feelings: {embrace_emotions}
- AVOID these feelings: {avoid_emotions}

LANGUAGE STYLE:
- USE words like: {embrace_language}
- NEVER use words like: {avoid_language}

PODCAST: {podcast.get('title', 'Daily Podcast')}
TARGET LENGTH: {episode.get('target_minutes', 4)} minutes when read aloud
PACING: {pacing.get('overall_tempo', 'unhurried')}

WRITING GUIDELINES:
{hints_text}

STRUCTURE:
1. Warm greeting with today's date (~15 seconds)
2. Weather segment with positive framing (~30 seconds) 
3. News stories - this is the main section (~2.5-3 minutes)
4. Encouraging closing (~30 seconds)

IMPORTANT:
- Write exactly as it should be spoken aloud
- Use natural speech patterns and contractions
- Use ellipsis (...) for natural pauses between sections
- Keep sentences short to medium length for easy listening

STORY COVERAGE (this is the main content - give each story proper attention):
- Each story should be 4-6 sentences minimum
- Start with what happened (the news), then add context or background
- Share why this matters or why it's exciting
- Add your genuine reaction, a fun fact, or connect it to the bigger picture
- Don't just summarize - bring the story to life with your personality

- End with an encouraging send-off that feels genuine, not cheesy
- AIM FOR ~600-700 WORDS TOTAL to hit the 4-minute target"""

    return system_prompt


def build_user_prompt(
    weather_text: str,
    items: list[ContentItem],
    config: dict,
) -> str:
    """Build the user prompt with weather and news content.
    
    Args:
        weather_text: Formatted weather description.
        items: List of selected content items.
        config: Full configuration dictionary.
    
    Returns:
        User prompt string.
    """
    vibe = config.get("vibe", {})
    voice_persona = vibe.get("voice_persona", {})
    
    # Get greeting and closing options
    greetings = voice_persona.get("greetings", ["Good morning."])
    closings = voice_persona.get("closings", ["Have a great day."])
    
    # Pick random greeting and closing for variety
    greeting_hint = random.choice(greetings)
    closing_hint = random.choice(closings)
    
    # Format today's date
    today = datetime.now()
    date_formatted = today.strftime("%A, %B %d, %Y")  # e.g., "Friday, December 13, 2025"
    
    # Format news items
    stories_text = ""
    for i, item in enumerate(items, 1):
        stories_text += f"""
Story {i}: {item.title}
Source: {item.source}
Summary: {item.summary}
"""
    
    user_prompt = f"""Please write today's podcast script.

DATE: {date_formatted}

WEATHER:
{weather_text}

TODAY'S POSITIVE STORIES:
{stories_text}

STYLE HINTS:
- Consider opening with something like: "{greeting_hint}"
- Consider closing with something like: "{closing_hint}"
- Use ... (ellipsis) between major sections for natural pacing

WORD TARGETS:
- Greeting + weather: ~80 words
- Each story: ~80-100 words (4-6 sentences each - don't rush!)
- Closing: ~50 words
- Total: ~600-700 words for a 4-minute episode

Elaborate on each story - add context, share why it matters, react to it. Make the listener feel something.

Write the complete script now, ready to be read aloud."""

    return user_prompt


def generate_script(
    weather_text: str,
    items: list[ContentItem],
    config: dict,
) -> dict:
    """Generate the podcast script using OpenAI.
    
    Args:
        weather_text: Formatted weather description.
        items: List of selected content items.
        config: Full configuration dictionary.
    
    Returns:
        Dict with 'script', 'system_prompt', 'user_prompt', and 'model'.
    """
    openai_config = config.get("openai", {})
    llm_config = openai_config.get("llm", {})
    model = llm_config.get("model", "gpt-4o-mini")
    
    # Build prompts
    system_prompt = build_system_prompt(config)
    user_prompt = build_user_prompt(weather_text, items, config)
    
    # Create OpenAI client (uses OPENAI_API_KEY env var)
    client = OpenAI()
    
    # Generate script
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=llm_config.get("temperature", 0.7),
        max_tokens=llm_config.get("max_tokens", 2000),
    )
    
    script = response.choices[0].message.content.strip()
    
    # Clean up any music cues or stage directions the AI might have added
    script = clean_script_for_tts(script)
    
    return {
        "script": script,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "model": model,
    }


def generate_episode_title(
    items: list[ContentItem],
    config: dict,
) -> str:
    """Generate a content-based episode title using AI.
    
    Args:
        items: List of selected content items for the episode.
        config: Full configuration dictionary.
    
    Returns:
        A concise, engaging episode title.
    """
    openai_config = config.get("openai", {})
    llm_config = openai_config.get("llm", {})
    model = llm_config.get("model", "gpt-4o-mini")
    
    # Build content summary for title generation
    content_summary = []
    for item in items[:5]:  # Use top 5 items
        content_summary.append(f"- {item.title}")
    
    content_text = "\n".join(content_summary)
    
    prompt = f"""Generate a concise, engaging podcast episode title (max 60 characters) based on today's content.

Content covered:
{content_text}

Requirements:
- Be specific and descriptive
- Highlight the most interesting/important topics
- Keep it under 60 characters
- Don't include the date or podcast name
- Make it compelling and clickable
- Use "&" to connect topics if needed

Examples of good titles:
- "NASA Mars Discovery & AI Medical Breakthrough"
- "Clean Energy Surge & NYC Green Initiative"
- "SpaceX Success & Revolutionary Battery Tech"

Generate only the title, no quotes or extra text:"""
    
    # Create OpenAI client
    client = OpenAI()
    
    # Generate title
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=50,
    )
    
    title = response.choices[0].message.content.strip()
    
    # Remove quotes if AI added them
    title = title.strip('"').strip("'")
    
    # Truncate if too long
    if len(title) > 60:
        title = title[:57] + "..."
    
    return title


def generate_script_dry_run(
    weather_text: str,
    items: list[ContentItem],
    config: dict,
) -> dict:
    """Generate a placeholder script for dry-run mode (no API call).
    
    Args:
        weather_text: Formatted weather description.
        items: List of selected content items.
        config: Full configuration dictionary.
    
    Returns:
        Dict with 'script', 'system_prompt', 'user_prompt', and 'model'.
    """
    vibe = config.get("vibe", {})
    voice_persona = vibe.get("voice_persona", {})
    greetings = voice_persona.get("greetings", ["Good morning."])
    closings = voice_persona.get("closings", ["Have a great day."])
    openai_config = config.get("openai", {})
    llm_config = openai_config.get("llm", {})
    model = llm_config.get("model", "gpt-4o-mini")
    
    today = datetime.now()
    date_formatted = today.strftime("%A, %B %d, %Y")
    
    # Build the prompts (even for dry run, so we can inspect them)
    system_prompt = build_system_prompt(config)
    user_prompt = build_user_prompt(weather_text, items, config)
    
    # Build a simple placeholder script
    script_lines = [
        f"[DRY RUN - Script would be generated here]",
        "",
        f"Date: {date_formatted}",
        f"Greeting: {random.choice(greetings)}",
        "",
        f"Weather: {weather_text}",
        "",
        "Stories:",
    ]
    
    for i, item in enumerate(items, 1):
        script_lines.append(f"  {i}. {item.title} ({item.source})")
    
    script_lines.extend([
        "",
        f"Closing: {random.choice(closings)}",
    ])
    
    return {
        "script": "\n".join(script_lines),
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "model": f"{model} [DRY RUN - not called]",
    }

