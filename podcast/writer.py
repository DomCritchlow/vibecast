"""Script generation with pluggable LLM providers (Anthropic Claude / OpenAI).

The writer is the voice of the show, so it defaults to the strongest
available model: Claude Opus 4.8 with adaptive thinking. If no Anthropic
credentials are configured the pipeline falls back to OpenAI so the nightly
run never fails on a missing key.

Configured via config.yaml:

    writer:
      provider: "anthropic"          # anthropic or openai
      anthropic:
        model: "claude-opus-4-8"
      openai:
        model: "gpt-5.4-mini"
"""

import json
import logging
import os
import random
import re
from datetime import datetime

from .sources.base import ContentItem

logger = logging.getLogger(__name__)

DEFAULT_ANTHROPIC_MODEL = "claude-opus-4-8"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"

TITLE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Episode title, max 60 characters, no date or podcast name",
        }
    },
    "required": ["title"],
    "additionalProperties": False,
}

QUALITY_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {
            "type": "number",
            "description": "0.0-1.0: how much today's lineup deserves the produced treatment",
        },
        "reason": {"type": "string", "description": "One sentence explaining the score"},
    },
    "required": ["score", "reason"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class AnthropicWriter:
    """Script writer backed by the Anthropic API (Claude)."""

    provider_name = "anthropic"

    def __init__(self, writer_config: dict):
        import anthropic

        self.model = (writer_config.get("anthropic") or {}).get("model", DEFAULT_ANTHROPIC_MODEL)
        self.client = anthropic.Anthropic()

    def generate_text(self, system: str, user: str, max_tokens: int = 4000) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return _first_text_block(response)

    def generate_json(self, system: str, user: str, schema: dict, max_tokens: int = 2000) -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        return json.loads(_first_text_block(response))


def _first_text_block(response) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    raise ValueError(f"No text block in response (stop_reason={response.stop_reason})")


class OpenAIWriter:
    """Script writer backed by the OpenAI API."""

    provider_name = "openai"

    def __init__(self, writer_config: dict):
        from openai import OpenAI

        openai_config = writer_config.get("openai") or {}
        self.model = openai_config.get("model", DEFAULT_OPENAI_MODEL)
        self.temperature = openai_config.get("temperature")
        self.client = OpenAI()

    def _sampling_params(self, max_tokens: int) -> dict:
        # gpt-5* and o* reasoning models reject `temperature` and use
        # `max_completion_tokens`; older chat models keep the classic params.
        if self.model.startswith(("gpt-5", "o")):
            return {"max_completion_tokens": max_tokens}
        params = {"max_tokens": max_tokens}
        if self.temperature is not None:
            params["temperature"] = self.temperature
        return params

    def generate_text(self, system: str, user: str, max_tokens: int = 4000) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            **self._sampling_params(max_tokens),
        )
        return response.choices[0].message.content.strip()

    def generate_json(self, system: str, user: str, schema: dict, max_tokens: int = 2000) -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "output", "strict": True, "schema": schema},
            },
            **self._sampling_params(max_tokens),
        )
        return json.loads(response.choices[0].message.content)


def _writer_config(config: dict) -> dict:
    """Read the writer config, falling back to the legacy openai.llm section."""
    writer_config = config.get("writer")
    if writer_config:
        return writer_config
    legacy_llm = (config.get("openai") or {}).get("llm") or {}
    return {"provider": "openai", "openai": legacy_llm}


def get_writer(config: dict):
    """Build the configured script writer, with a safe fallback to OpenAI."""
    writer_config = _writer_config(config)
    provider = writer_config.get("provider", "anthropic")

    if provider == "anthropic":
        if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            return AnthropicWriter(writer_config)
        logger.warning(
            "writer.provider is 'anthropic' but no ANTHROPIC_API_KEY is set; falling back to OpenAI"
        )
    elif provider != "openai":
        logger.warning("Unknown writer provider '%s', using OpenAI", provider)

    return OpenAIWriter(writer_config)


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def clean_script_for_tts(script: str, keep_production_cues: bool = False) -> str:
    """Remove non-speakable elements from script before TTS.

    With ``keep_production_cues`` (special/produced episodes), [SFX: ...]
    cue lines and Eleven v3 audio tags like [chuckles] are left in place —
    the production pipeline consumes them.
    """
    # Remove music cues like [intro music], [outro music], [background music fades]
    script = re.sub(
        r"\[(?:intro|outro|background)?\s*music[^\]]*\]", "", script, flags=re.IGNORECASE
    )
    # Remove other stage directions like [fade out], [transition], [cut to]
    script = re.sub(r"\[(?:fade|cut|transition|end|start)[^\]]*\]", "", script, flags=re.IGNORECASE)
    # Convert [pause] markers to ellipsis (which TTS interprets as natural pause)
    script = re.sub(r"\[pause[^\]]*\]", "...", script, flags=re.IGNORECASE)
    if not keep_production_cues:
        # Strip stray production cues — plain TTS providers would read them
        # aloud... or worse, spell them out.
        script = re.sub(
            r"^[ \t]*\[(?:sfx|ambience):[^\]]*\][ \t]*$",
            "",
            script,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    # Clean up extra whitespace/newlines left behind
    script = re.sub(r"\n{3,}", "\n\n", script)
    script = re.sub(r"  +", " ", script)
    return script.strip()


def _sound_shelf_prompt(sound_config: dict) -> str:
    """List the sound library so the writer can reuse existing material.

    A verbatim reuse is a cache hit (no generation); anything new is
    generated and joins the shelf for future episodes.
    """
    try:
        from .production import load_library_index, sfx_library_dir

        entries = load_library_index(sfx_library_dir(sound_config))
    except Exception:
        return ""
    if not entries:
        return ""

    beds = [e["direction"] for e in entries if e.get("loop") and e.get("direction")][-10:]
    effects = [e["direction"] for e in entries if not e.get("loop") and e.get("direction")][-15:]

    lines = [
        "",
        "",
        "THE SHELF — sounds already produced for past episodes. If one fits today, "
        "reuse it by writing its description word-for-word; otherwise direct a new "
        "sound and it joins the shelf. Fit beats reuse: never bend today's episode "
        "to match the shelf.",
    ]
    if beds:
        lines.append("Ambience beds:")
        lines.extend(f"- {b}" for b in beds)
    if effects:
        lines.append("Effects:")
        lines.extend(f"- {e}" for e in effects)
    return "\n".join(lines)


def build_production_prompt(config: dict) -> str:
    """Extra system-prompt section for produced (ElevenLabs) episodes.

    Special episodes are voiced by Eleven v3, which performs inline audio
    tags, and run through a sound-design mix that turns [SFX: ...] cue lines
    into generated effects under the voice.
    """
    special = (config.get("tts") or {}).get("special_episodes") or {}
    sound = special.get("sound_design") or {}
    max_effects = sound.get("max_effects", 4)

    return f"""

AUDIO PRODUCTION (today is a produced episode — you also direct the audio):

Delivery tags. You may drop inline audio tags in square brackets to direct \
your own performance: [chuckles], [laughs], [sighs], [whispers], [excited], \
[curious], [deadpan], [impressed]. The voice engine performs them — they are \
never read aloud. Use them like seasoning: a small handful per episode, at \
most one per paragraph, only where the writing genuinely earns it.

Opening ambience. You direct the bed that plays under your cold open. Put one \
line at the very top of the script, before any spoken text:

[AMBIENCE: the sound of the morning you're speaking into]

Make it specific to today — the weather, the season, the mood of the lead \
story. "Gentle rain over a quiet street, a distant subway rumble" beats \
"city sounds". It plays low under your first ~15 seconds and fades out. \
Describe sound only, never music.

Sound-effect cues. You may add up to {max_effects} sound-effect cues. Each cue \
goes on its own line between paragraphs, exactly in this form:

[SFX: short description of an atmospheric sound]

By default the effect is mixed quietly UNDER the lines that follow it, so place \
a cue right before the sentences it should color — e.g. "[SFX: distant rocket \
launch rumble]" before a launch story. Prefer texture over spectacle; one \
well-placed cue beats four. Skip them for stories where sound would feel forced.

Featured beats. Rarely — once in an episode at most, and only when a moment \
truly lands — you can give an effect its own beat by adding "| beat":

[SFX: distant rocket launch rumble | beat]

A beat pauses your narration for a moment so the sound plays in the clear \
before you continue, the way a well-produced show lets a moment breathe. Use it \
for a genuine punctuation point — a launch, a thunderclap, a reveal — never for \
background texture. Most cues should NOT be beats. Never cue music.\
{_sound_shelf_prompt(sound)}"""


def build_system_prompt(config: dict, special: bool = False) -> str:
    """Build the system prompt based on vibe configuration."""
    vibe = config.get("vibe", {})
    episode = config.get("episode", {})
    podcast = config.get("podcast", {})

    mood = vibe.get("mood", {})
    voice_persona = vibe.get("voice_persona", {})
    avoid = vibe.get("avoid", {})
    embrace = vibe.get("embrace", {})
    pacing = episode.get("pacing", {})

    personality_lines = voice_persona.get("personality", [])
    personality_text = "\n".join(f"- {p}" for p in personality_lines)

    avoid_emotions = ", ".join(avoid.get("emotions", []))
    avoid_language = ", ".join(avoid.get("language", []))
    embrace_emotions = ", ".join(embrace.get("emotions", []))
    embrace_language = ", ".join(embrace.get("language", []))

    script_hints = _writer_config(config).get("script_hints") or config.get("openai", {}).get(
        "script_hints", []
    )
    hints_text = "\n".join(f"- {h}" for h in script_hints)

    target_minutes = episode.get("target_minutes", 5)
    word_target = f"{target_minutes * 150}-{target_minutes * 180}"

    prompt = f"""You are {voice_persona.get("name", "a podcast host")}, and you write and host \
"{podcast.get("title", "a daily podcast")}" — a short daily audio essay about what's genuinely \
interesting in tech and science.

This is narrative radio, not a news rundown. Your models are independent audio \
journalists — the reporter who's been following something all week and can't wait to tell \
you the fascinating part. One person talking to one listener, with craft.

PERSONALITY:
{personality_text}

MOOD: {mood.get("primary", "curious")}, {mood.get("secondary", "informed")} — {mood.get("energy", "engaged-but-chill")}

THE CRAFT:

Find the thread. Look at today's material and find the idea, tension, or pattern that \
connects some of it. Let that thread give the episode its shape. The show is called \
"Morning Thread" for a reason. If nothing truly connects, pick the strongest story as \
your spine and let the others orbit it — never force a fake connection.

Open cold. Start inside the most interesting story: a concrete detail, an image, a number \
that shouldn't be possible, a question. Never open with a canned greeting, the date, or \
the weather. You can say who you are and what day it is in passing once we're already \
hooked — a phrase, not an announcement.

Weight stories by how interesting they are, not equally. Your lead deserves real time — \
context, a specific detail or two, why it matters. A minor story might earn one great \
sentence. It's better to say something sharp about four stories than something forgettable \
about seven. You may skip a story entirely if it doesn't earn its airtime.

Transitions ride ideas, not formats. Move between stories through what they share — a \
theme, an irony, a contrast. Never "in other news," "next up," "moving on," "speaking of," \
or numbered stories.

Weather is texture, not a segment. Work it in as one natural line wherever it fits — the \
way a friend would mention it — or as a grace note at the end.

Land the ending. Close by returning to the thread, or leaving the listener with one thought \
worth carrying into their day. No broadcast sign-offs, no "that's all for today," no recap.

WRITE FOR THE EAR:
{hints_text}
- Read it aloud in your head; if a sentence trips, rewrite it
- Mix short sentences with long ones — rhythm is everything
- Contractions always; concrete nouns and real numbers over abstractions
- Feelings to reach for: {embrace_emotions}. Never: {avoid_emotions}
- Words that fit the show: {embrace_language}. Words that never appear: {avoid_language}

HARD CONSTRAINTS:
- {"Only spoken text plus the audio tags and [SFX: ...] cues described below — no music cues, headings, or labels" if special else "Only text meant to be spoken aloud — no music cues, stage directions, headings, or labels"}
- Mention the show/host identity and today's date somewhere in the first minute, naturally
- {word_target} words total (about {target_minutes} minutes read aloud, {pacing.get("overall_tempo", "unhurried")} pace)"""

    if special:
        prompt += build_production_prompt(config)
    return prompt


def build_user_prompt(
    weather_text: str,
    items: list[ContentItem],
    config: dict,
    reading_items: list | None = None,
) -> str:
    """Build the user prompt with today's raw material."""
    date_formatted = datetime.now().strftime("%A, %B %d, %Y")

    stories_text = ""
    for item in items:
        stories_text += f"""
— {item.title} ({item.source})
  {item.summary}
"""

    reading_text = ""
    if reading_items:
        reading_text = (
            "\nFOR THE READING RECOMMENDATION (pick ONE that best fits today's thread and "
            "give it a sentence or two — it's something for listeners to read later, "
            "not for you to summarize):\n"
        )
        for item in reading_items:
            author_info = f" by {item.author}" if getattr(item, "author", "") else ""
            description = f" ({item.description})" if getattr(item, "description", "") else ""
            reading_text += f"""
— {item.title}{author_info} ({item.source}{description})
  {item.summary[:300]}
"""

    return f"""Here is today's raw material. Find the thread and write the episode.

DATE: {date_formatted}

WEATHER (one natural line, wherever it fits):
{weather_text}

TODAY'S STORIES (in no particular order — you decide what leads, what gets a beat,
and what gets cut):
{stories_text}{reading_text}
You choose the structure. Take a moment to find the throughline and the cold open
before you write. Then write the complete script, ready to be read aloud."""


# ---------------------------------------------------------------------------
# Generation entry points
# ---------------------------------------------------------------------------


def generate_script(
    weather_text: str,
    items: list[ContentItem],
    config: dict,
    reading_items: list | None = None,
    special: bool = False,
) -> dict:
    """Generate the podcast script with the configured writer.

    With ``special`` the prompt gains the audio-production section and the
    script keeps its audio tags and [SFX: ...] cues for the produced pipeline.

    Returns:
        Dict with 'script', 'system_prompt', 'user_prompt', 'model', 'provider'.
    """
    writer = get_writer(config)
    system_prompt = build_system_prompt(config, special=special)
    user_prompt = build_user_prompt(weather_text, items, config, reading_items)

    logger.info(
        "Generating %sscript with %s (%s)",
        "produced-episode " if special else "",
        writer.provider_name,
        writer.model,
    )
    script = writer.generate_text(system_prompt, user_prompt)
    script = clean_script_for_tts(script, keep_production_cues=special)

    return {
        "script": script,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "model": writer.model,
        "provider": writer.provider_name,
        "special": special,
    }


def score_episode_quality(items: list[ContentItem], config: dict) -> float:
    """Rate how much today's lineup deserves the produced treatment (0.0-1.0).

    Acts as the show's executive producer: high scores are reserved for days
    with a genuinely standout, fascinating, or landmark story. Failures score
    0.0 so a broken call never spends the week's special budget by accident.
    """
    writer = get_writer(config)

    content_text = "\n".join(
        f"- {item.title} ({item.source}): {item.summary[:200]}" for item in items
    )

    system = (
        "You are the executive producer of a daily tech and science podcast. You decide "
        "which days earn the full produced treatment — original music, sound design, and the "
        "premium voice — that is reserved for standout episodes, not ordinary good days."
    )
    user = f"""Rate today's story lineup from 0.0 to 1.0 on how much it deserves the special \
produced treatment versus a normal episode.

Guidance:
- 0.8-1.0: a genuinely big, fascinating, or landmark day — a story people will remember, or \
a lineup that's a clear cut above.
- 0.5-0.7: a solid, interesting day, but nothing extraordinary.
- below 0.5: a routine or slow news day.

Be discerning — most days are not special. Reserve high scores for lineups that truly stand out.

TODAY'S STORIES:
{content_text}"""

    try:
        result = writer.generate_json(system, user, QUALITY_SCHEMA, max_tokens=1500)
        score = float(result.get("score", 0.0))
        reason = result.get("reason", "")
        logger.info("Quality score %.2f — %s", score, reason)
        return max(0.0, min(1.0, score))
    except Exception as e:
        logger.warning("Quality scoring failed (%s); treating today as not special", e)
        return 0.0


def generate_episode_title(items: list[ContentItem], config: dict) -> str:
    """Generate a content-based episode title with the configured writer."""
    writer = get_writer(config)

    content_text = "\n".join(f"- {item.title}" for item in items[:5])

    system = "You write concise, compelling podcast episode titles."
    user = f"""Generate a concise, engaging podcast episode title (max 60 characters) based on today's content.

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
- "SpaceX Success & Revolutionary Battery Tech\""""

    try:
        result = writer.generate_json(system, user, TITLE_SCHEMA, max_tokens=1000)
        title = result["title"].strip().strip('"').strip("'")
    except Exception as e:
        logger.warning("Title generation failed (%s); using first story title", e)
        title = items[0].title if items else "Daily Episode"

    if len(title) > 60:
        title = title[:57] + "..."
    return title


def generate_script_dry_run(
    weather_text: str,
    items: list[ContentItem],
    config: dict,
    reading_items: list | None = None,
    special: bool = False,
) -> dict:
    """Generate a placeholder script for dry-run mode (no API call)."""
    voice_persona = config.get("vibe", {}).get("voice_persona", {})
    greetings = voice_persona.get("greetings", ["Good morning."])
    closings = voice_persona.get("closings", ["Have a great day."])
    writer_config = _writer_config(config)
    provider = writer_config.get("provider", "anthropic")
    model = (writer_config.get(provider) or {}).get(
        "model", DEFAULT_ANTHROPIC_MODEL if provider == "anthropic" else DEFAULT_OPENAI_MODEL
    )

    date_formatted = datetime.now().strftime("%A, %B %d, %Y")

    # Build the prompts (even for dry run, so we can inspect them)
    system_prompt = build_system_prompt(config, special=special)
    user_prompt = build_user_prompt(weather_text, items, config, reading_items)

    script_lines = [
        "[DRY RUN - Script would be generated here]",
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

    if reading_items:
        script_lines.append("")
        script_lines.append("Reading List:")
        for i, item in enumerate(reading_items, 1):
            author = f" by {item.author}" if getattr(item, "author", "") else ""
            script_lines.append(f"  {i}. {item.title}{author} ({item.source})")

    script_lines.extend(["", f"Closing: {random.choice(closings)}"])

    return {
        "script": "\n".join(script_lines),
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "model": f"{model} [DRY RUN - not called]",
        "provider": provider,
        "special": special,
    }
