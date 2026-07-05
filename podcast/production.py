"""Produced ("special") episodes: ElevenLabs voice + sound design.

On special days the episode is assembled like a small radio piece instead of
a single TTS pass:

- The script is voiced with ElevenLabs (v3 audio tags left intact, no
  post-processing — the voice is used exactly as the API returns it).
- ``[SFX: ...]`` cue lines written by the script writer become generated
  sound effects, mixed under the voice at the moment the cue appears.
- A weather-matched ambience bed plays under the cold open.
- An optional theme sting (a committed asset, see scripts/generate_theme.py)
  opens the show.

Everything besides the voice is optional and degrades gracefully: if an
effect fails to generate or ffmpeg is unavailable, the episode ships as
plain voice audio rather than failing the run.
"""

import json
import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent

# SFX cues live on their own line: [SFX: distant rocket launch rumble]
SFX_CUE_RE = re.compile(r"^[ \t]*\[sfx:\s*(?P<desc>[^\]]+)\][ \t]*$", re.IGNORECASE | re.MULTILINE)

# The writer directs the opening bed itself: [AMBIENCE: rain over a quiet street]
AMBIENCE_CUE_RE = re.compile(
    r"^[ \t]*\[ambience:\s*(?P<desc>[^\]]+)\][ \t]*$", re.IGNORECASE | re.MULTILINE
)

# Looping is only supported by the v2 sound model, so pin it when we loop.
SFX_LOOP_MODEL = "eleven_text_to_sound_v2"

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


# ---------------------------------------------------------------------------
# Config / scheduling
# ---------------------------------------------------------------------------


def special_config(config: dict) -> dict:
    return (config.get("tts") or {}).get("special_episodes") or {}


def specials_this_week(state: dict, today: datetime) -> int:
    """How many produced episodes have already shipped this ISO week."""
    year, week, _ = today.isocalendar()
    count = 0
    for date_str in (state or {}).get("special_dates", []):
        try:
            when = datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            continue
        y, w, _ = when.isocalendar()
        if (y, w) == (year, week):
            count += 1
    return count


def is_special_episode(
    config: dict,
    today: datetime,
    *,
    state: dict | None = None,
    quality_score: float | None = None,
    force: bool | None = None,
) -> bool:
    """Decide whether today gets the produced treatment.

    Precedence:
      1. CLI --special/--no-special (``force``) always wins.
      2. Disabled, or the week's budget is already spent → no.
      3. A ``quality_score`` at/above the gate threshold → yes. This is how a
         standout weekday gets promoted and spends the week's slot.
      4. The use-it-or-lose-it ``fallback_day`` (e.g. Friday) → yes, so a quiet
         news week still gets its one produced episode.

    Args:
        config: Full configuration dict.
        today: The episode date.
        state: Pipeline state (holds this week's already-produced dates).
        quality_score: Producer's 0–1 rating of today's lineup, or None to
            skip the quality gate (e.g. dry runs).
        force: CLI override — True forces special, False forces normal.
    """
    if force is not None:
        return force

    special = special_config(config)
    if not special.get("enabled", False):
        return False

    budget = int(special.get("weekly_budget", 1))
    if specials_this_week(state or {}, today) >= budget:
        return False

    gate = special.get("quality_gate") or {}
    if (
        gate.get("enabled", True)
        and quality_score is not None
        and quality_score >= float(gate.get("threshold", 0.8))
    ):
        return True

    fallback = special.get("fallback_day")
    return bool(fallback and WEEKDAYS[today.weekday()] == str(fallback).lower())


# ---------------------------------------------------------------------------
# Script cue parsing
# ---------------------------------------------------------------------------


@dataclass
class ScriptPart:
    """A segment of the parsed script: spoken text or an SFX cue.

    ``hold`` (SFX only) marks a "featured" effect: the voice pauses for a
    deliberate beat so the sound lands in the clear before narration resumes,
    the way a produced show breathes. Plain cues stay as under-voice texture.
    """

    kind: str  # "voice" | "sfx"
    text: str  # spoken text, or the SFX description
    hold: bool = False


def _parse_sfx_modifier(desc: str) -> tuple[str, bool]:
    """Split an SFX description from its optional ``| beat`` / ``| hold`` flag."""
    segments = re.split(r"\s*\|\s*", desc)
    text = segments[0].strip()
    hold = any(seg.strip().lower() in ("beat", "hold") for seg in segments[1:])
    return text, hold


def parse_script_cues(script: str, max_effects: int = 4) -> list[ScriptPart]:
    """Split a script into voice segments and SFX cues, in order.

    Cues beyond ``max_effects`` are dropped (the writer is told the limit,
    but models drift). Empty voice segments are skipped.
    """
    parts: list[ScriptPart] = []
    effects = 0
    cursor = 0

    for match in SFX_CUE_RE.finditer(script):
        voice_text = script[cursor : match.start()].strip()
        if voice_text:
            parts.append(ScriptPart("voice", voice_text))
        cursor = match.end()

        if effects < max_effects:
            text, hold = _parse_sfx_modifier(match.group("desc").strip())
            parts.append(ScriptPart("sfx", text, hold=hold))
            effects += 1
        else:
            logger.warning("Dropping extra SFX cue beyond limit: %s", match.group("desc"))

    tail = script[cursor:].strip()
    if tail:
        parts.append(ScriptPart("voice", tail))

    return parts


def strip_sfx_cues(script: str) -> str:
    """Remove SFX/ambience cue lines (for anything that speaks everything)."""
    stripped = AMBIENCE_CUE_RE.sub("", SFX_CUE_RE.sub("", script))
    return re.sub(r"\n{3,}", "\n\n", stripped).strip()


def strip_production_markup(script: str) -> str:
    """Plain spoken text with ALL production markup removed.

    For handing a produced-episode script (audio tags, SFX/ambience cues) to
    a TTS provider that would read brackets aloud — the normal-episode
    fallback path.
    """
    script = strip_sfx_cues(script)
    script = re.sub(r"\[[^\]]{0,60}\]", "", script)
    return re.sub(r"  +", " ", re.sub(r"\n{3,}", "\n\n", script)).strip()


def parse_ambience_cue(script: str) -> tuple[str | None, str]:
    """Pull the writer's [AMBIENCE: ...] direction out of the script.

    Returns (description or None, script with all ambience lines removed).
    Only the first cue counts — there is one opening bed per episode.
    """
    match = AMBIENCE_CUE_RE.search(script)
    remaining = re.sub(r"\n{3,}", "\n\n", AMBIENCE_CUE_RE.sub("", script)).strip()
    return (match.group("desc").strip() if match else None), remaining


# ---------------------------------------------------------------------------
# Weather ambience
# ---------------------------------------------------------------------------

_AMBIENCE_RULES = [
    (("thunder",), "distant rolling thunder with steady rain on city windows"),
    (("rain", "drizzle", "shower"), "gentle rain falling on a city street, soft and steady"),
    (
        (
            "snow",
            "flurr",
        ),
        "hushed snowy city morning, muffled footsteps, soft wind",
    ),
    (("fog", "mist"), "muted foggy morning in a city, distant foghorn, soft air"),
    (("wind", "gust", "breez"), "wind moving through city streets and trees"),
    (("storm",), "far-off storm ambience, low rumbles, wind picking up"),
    (("clear", "sunny", "sunshine"), "bright city morning, birds chirping, light distant traffic"),
    (("cloud", "overcast"), "calm overcast city morning, soft distant traffic hum"),
    (("hot", "heat", "humid"), "warm summer morning in the city, cicadas, lazy distant traffic"),
]

_DEFAULT_AMBIENCE = "quiet city morning ambience, distant traffic, a few birds"


def weather_ambience_prompt(weather_text: str) -> str:
    """Map the episode's weather line to a sound-effect prompt for the open."""
    lowered = (weather_text or "").lower()
    for keywords, prompt in _AMBIENCE_RULES:
        if any(k in lowered for k in keywords):
            return f"{prompt}{AMBIENCE_SUFFIX}"
    return f"{_DEFAULT_AMBIENCE}{AMBIENCE_SUFFIX}"


# ---------------------------------------------------------------------------
# ffmpeg helpers
# ---------------------------------------------------------------------------


def _ffmpeg_available() -> bool:
    try:
        return (
            subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5).returncode == 0
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _probe_duration(path: Path) -> float:
    """Audio duration in seconds via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return float(result.stdout.strip())


# ---------------------------------------------------------------------------
# Sound-effect generation (transport-selectable: fal or elevenlabs)
# ---------------------------------------------------------------------------


def _generate_sfx(prompt: str, seconds: float, loop: bool, provider: str) -> bytes:
    """Generate one sound effect via the chosen transport (callers catch)."""
    logger.info("  SFX (%ss%s, %s): %s", seconds, ", loop" if loop else "", provider, prompt)

    if provider == "fal":
        from .tts.fal_tts import fal_sound_effect

        return fal_sound_effect(prompt, seconds, loop)

    # Native ElevenLabs SDK (kept as a switch-back option).
    from elevenlabs import ElevenLabs

    kwargs = {"text": prompt, "duration_seconds": seconds, "prompt_influence": 0.5}
    if loop:
        kwargs["loop"] = True
        kwargs["model_id"] = SFX_LOOP_MODEL
    return b"".join(ElevenLabs().text_to_sound_effects.convert(**kwargs))


# ---------------------------------------------------------------------------
# Sound library (cache-first reuse of generated effects)
# ---------------------------------------------------------------------------


# Steers the SFX model toward beds; stripped back off for shelf listings so
# the writer sees (and can reuse verbatim) the bare direction it would write.
AMBIENCE_SUFFIX = ", ambient bed, no music"


def sfx_library_dir(sound_config: dict) -> Path | None:
    """The committed library directory, or None if reuse is disabled."""
    if not sound_config.get("library", True):
        return None
    return REPO_ROOT / sound_config.get("library_dir", "podcast/assets/sfx")


def load_library_index(library_dir: Path | None) -> list[dict]:
    """Entries of the sound library's index.json (empty if none yet)."""
    if library_dir is None:
        return []
    path = library_dir / "index.json"
    if not path.exists():
        return []
    try:
        entries = json.loads(path.read_text())
        return entries if isinstance(entries, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _record_in_library_index(
    library_dir: Path, filename: str, prompt: str, seconds: float, loop: bool
) -> None:
    """Add a generated sound to index.json so the writer can see the shelf."""
    entries = [e for e in load_library_index(library_dir) if e.get("file") != filename]
    entries.append(
        {
            "file": filename,
            "prompt": prompt,
            "direction": prompt.removesuffix(AMBIENCE_SUFFIX),
            "seconds": seconds,
            "loop": loop,
        }
    )
    (library_dir / "index.json").write_text(json.dumps(entries, indent=1) + "\n")


def sfx_library_path(library_dir: Path, prompt: str, seconds: float, loop: bool) -> Path:
    """Deterministic library filename for a generation request.

    Human-readable slug up front so the library is browsable; short hash of
    the full request at the end so truncated slugs can't collide.
    """
    import hashlib

    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower()).strip("-")[:60].rstrip("-")
    digest = hashlib.sha1(f"{prompt}|{seconds:g}|{loop}".encode()).hexdigest()[:8]
    suffix = f"{int(seconds)}s" + ("-loop" if loop else "")
    return library_dir / f"{slug}--{suffix}-{digest}.mp3"


def _get_or_generate_sfx(
    prompt: str, seconds: float, loop: bool, library_dir: Path | None, provider: str
) -> bytes:
    """Reuse an effect from the library, generating (and saving) on a miss.

    The library is transport-independent — the same ElevenLabs model backs
    both fal and the native SDK — so a cached effect is reused regardless of
    which provider produced it.
    """
    if library_dir is None:
        return _generate_sfx(prompt, seconds, loop, provider)

    path = sfx_library_path(library_dir, prompt, seconds, loop)
    if path.exists():
        logger.info("  SFX library hit: %s", path.name)
        return path.read_bytes()

    audio = _generate_sfx(prompt, seconds, loop, provider)
    library_dir.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)
    _record_in_library_index(library_dir, path.name, prompt, seconds, loop)
    logger.info("  SFX saved to library: %s", path.name)
    return audio


# ---------------------------------------------------------------------------
# Production pipeline
# ---------------------------------------------------------------------------


def build_timeline(
    parts: list[ScriptPart],
    voice_files: list[Path],
    voice_durations: list[float],
    generated: dict[int, tuple[Path, float]],
    theme_lead: float,
    spotlight_seconds: float,
    lead_seconds: float = 0.0,
) -> tuple[list[tuple[Path, float, bool]], list[tuple[Path, float, bool, float]]]:
    """Place voice segments and effects on a shared timeline.

    Voice segments play back to back starting after the theme lead-in. A
    featured (``hold``) effect pauses the narration only for its spotlight:
    after a ``lead_seconds`` breath the sound starts, plays alone for
    ``spotlight_seconds``, then the voice resumes — while the sound's tail
    keeps playing underneath (the mix ducks it). So the voice gap is just
    ``lead_seconds + spotlight_seconds``, independent of how long the sound
    itself runs. Effects whose generation failed (absent from ``generated``)
    are skipped and add no pause.

    A voice segment that resumes after a spotlight is flagged for a gentle
    fade-in so it eases in over the ducked tail rather than hard-cutting.

    Returns:
        (voice_placements, sfx_placements):
          - voice_placements: (file, start_seconds, fade_in)
          - sfx_placements: (file, start_seconds, featured, duration_seconds)
    """
    voice_placements: list[tuple[Path, float, bool]] = []
    sfx_placements: list[tuple[Path, float, bool, float]] = []
    timeline = theme_lead
    voice_index = 0
    fade_next_voice = False

    for idx, part in enumerate(parts):
        if part.kind == "voice":
            voice_placements.append((voice_files[voice_index], timeline, fade_next_voice))
            timeline += voice_durations[voice_index]
            voice_index += 1
            fade_next_voice = False
            continue

        placed = generated.get(idx)
        if placed is None:
            continue
        path, seconds = placed
        # A featured effect gets a lead breath after the voice ends; an
        # under-voice effect starts right where its cue sat.
        start = timeline + lead_seconds if part.hold else timeline
        sfx_placements.append((path, start, part.hold, seconds))
        if part.hold:
            # The voice pauses only for the lead breath + the spotlight; the
            # sound's tail (seconds - spotlight) then runs ducked under the
            # resuming, gently faded-in voice.
            timeline += lead_seconds + spotlight_seconds
            fade_next_voice = True
            logger.info(
                "  Featured beat: %.1fs spotlight, %.1fs sound: %s",
                spotlight_seconds,
                seconds,
                part.text,
            )

    return voice_placements, sfx_placements


def produce_special_episode(
    script: str,
    weather_text: str,
    config: dict,
) -> tuple[bytes, float | None]:
    """Voice + mix a produced episode.

    Returns:
        (mp3_bytes, duration_seconds) — duration measured from the final
        file when ffmpeg is available, else None.
    """
    from .tts import get_tts_provider, preprocess_for_tts

    special = special_config(config)
    sound = special.get("sound_design") or {}

    # One provider name drives both voice and sound design. "fal" is the
    # no-subscription transport; "elevenlabs" is the native SDK switch-back.
    provider_name = special.get("provider", "fal")
    provider = get_tts_provider(config, provider_name=provider_name)
    logger.info("Produced-episode transport: %s", provider.name)
    ambience_direction, script = parse_ambience_cue(script)
    parts = parse_script_cues(script, max_effects=int(sound.get("max_effects", 4)))
    voice_parts = [p for p in parts if p.kind == "voice"]
    sfx_cues = [p for p in parts if p.kind == "sfx"]
    logger.info(
        "Producing special episode: %d voice segment(s), %d SFX cue(s)",
        len(voice_parts),
        len(sfx_cues),
    )

    # --- Voice: raw provider output, no enhancement ---
    voice_audio = [provider.synthesize(preprocess_for_tts(p.text)) for p in voice_parts]

    mixing_possible = _ffmpeg_available()
    sound_enabled = bool(sound.get("enabled", True)) and mixing_possible
    if not mixing_possible:
        logger.warning("ffmpeg unavailable — shipping plain voice audio without sound design")

    plain_voice = b"".join(voice_audio)
    if not sound_enabled:
        return plain_voice, None

    library_dir = sfx_library_dir(sound)

    with tempfile.TemporaryDirectory(prefix="vibecast-production-") as tmp:
        tmpdir = Path(tmp)

        # Write voice segments and measure them so cue offsets are exact.
        voice_files, voice_durations = [], []
        for i, audio in enumerate(voice_audio):
            path = tmpdir / f"voice-{i:02d}.mp3"
            path.write_bytes(audio)
            voice_files.append(path)
            voice_durations.append(_probe_duration(path))

        # --- Theme sting (optional committed asset) ---
        theme_cfg = sound.get("theme") or {}
        theme_path = REPO_ROOT / theme_cfg.get("path", "podcast/assets/theme.mp3")
        theme_lead = 0.0
        theme_file = None
        if theme_path.exists():
            theme_file = theme_path
            theme_lead = float(theme_cfg.get("lead_seconds", 2.5))
        elif theme_cfg.get("path"):
            logger.info("No theme asset at %s — skipping sting", theme_path)

        # --- Weather ambience bed (optional) ---
        ambience_file = None
        ambience_seconds = float(sound.get("ambience_seconds", 15))
        if sound.get("weather_ambience", True):
            try:
                # The writer's own direction wins; the weather keyword map is
                # the fallback when the script didn't call an ambience.
                if ambience_direction:
                    prompt = f"{ambience_direction}{AMBIENCE_SUFFIX}"
                    logger.info("  Ambience directed by writer: %s", ambience_direction)
                else:
                    prompt = weather_ambience_prompt(weather_text)
                    logger.info("  Ambience from weather fallback")
                audio = _get_or_generate_sfx(
                    prompt,
                    ambience_seconds,
                    loop=True,
                    library_dir=library_dir,
                    provider=provider_name,
                )
                ambience_file = tmpdir / "ambience.mp3"
                ambience_file.write_bytes(audio)
            except Exception as e:
                logger.warning("Ambience generation failed (%s) — continuing without it", e)

        # --- Story SFX cues ---
        # A featured ("| beat") effect plays at its natural length: a short
        # spotlight in the clear, then the tail ducks under the resuming voice.
        # An ordinary cue is a quieter texture layered under the voice.
        effect_seconds = float(sound.get("effect_seconds", 5))
        feature_effect_seconds = float(sound.get("feature_effect_seconds", 5.0))
        spotlight_seconds = float(sound.get("spotlight_seconds", 2.0))
        lead_seconds = float(sound.get("lead_seconds", 0.5))

        # Generate effects first so a failed one neither plays nor holds a beat.
        generated: dict[int, tuple[Path, float]] = {}  # part index -> (file, seconds)
        for idx, part in enumerate(parts):
            if part.kind != "sfx":
                continue
            seconds = feature_effect_seconds if part.hold else effect_seconds
            try:
                audio = _get_or_generate_sfx(
                    part.text,
                    seconds,
                    loop=False,
                    library_dir=library_dir,
                    provider=provider_name,
                )
            except Exception as e:
                logger.warning("SFX generation failed (%s): %s", e, part.text)
                continue
            path = tmpdir / f"sfx-{len(generated):02d}.mp3"
            path.write_bytes(audio)
            generated[idx] = (path, seconds)

        voice_placements, sfx_placements = build_timeline(
            parts,
            voice_files,
            voice_durations,
            generated,
            theme_lead,
            spotlight_seconds,
            lead_seconds=lead_seconds,
        )

        output = tmpdir / "episode.mp3"
        try:
            _mix_episode(
                output=output,
                voice_placements=voice_placements,
                theme_file=theme_file,
                theme_cfg=theme_cfg,
                theme_lead=theme_lead,
                ambience_file=ambience_file,
                ambience_seconds=ambience_seconds,
                ambience_volume=float(sound.get("ambience_volume", 0.18)),
                sfx_placements=sfx_placements,
                effect_volume=float(sound.get("effect_volume", 0.28)),
                feature_volume=float(sound.get("feature_volume", 0.85)),
                duck_volume=float(sound.get("duck_volume", 0.22)),
                spotlight_seconds=spotlight_seconds,
                normalize=bool(sound.get("normalize", True)),
            )
        except Exception as e:
            logger.warning("Mixing failed (%s) — shipping plain voice audio", e)
            return plain_voice, None

        return output.read_bytes(), _probe_duration(output)


def _mix_episode(
    output: Path,
    voice_placements: list[tuple[Path, float, bool]],
    theme_file: Path | None,
    theme_cfg: dict,
    theme_lead: float,
    ambience_file: Path | None,
    ambience_seconds: float,
    ambience_volume: float,
    sfx_placements: list[tuple[Path, float, bool, float]],
    effect_volume: float,
    feature_volume: float,
    duck_volume: float,
    spotlight_seconds: float,
    normalize: bool,
) -> None:
    """Mix a timeline of voice segments, theme, ambience, and SFX to one MP3.

    Everything is a positioned input: each voice segment and each effect is
    delayed to its start time and summed. A featured effect plays at
    ``feature_volume`` for ``spotlight_seconds`` (in the clear), then ducks to
    ``duck_volume`` right as the voice resumes and its tail continues under the
    narration before fading out.

    Args:
        voice_placements: (file, start_seconds, fade_in) per voice segment.
        sfx_placements: (file, start_seconds, featured, duration_seconds) per effect.
    """
    inputs: list[str] = []
    filters: list[str] = []
    labels: list[str] = []
    index = 0

    for i, (path, start, fade_in) in enumerate(voice_placements):
        inputs += ["-i", str(path)]
        stages = []
        if fade_in:
            # Ease back in after a beat's silence instead of hard-cutting.
            stages.append("afade=t=in:d=0.2")
        if start > 0:
            stages.append(f"adelay=delays={int(start * 1000)}:all=1")
        chain = ",".join(stages) if stages else "acopy"
        filters.append(f"[{index}:a]{chain}[v{i}]")
        labels.append(f"[v{i}]")
        index += 1

    if theme_file is not None:
        inputs += ["-i", str(theme_file)]
        fade = float(theme_cfg.get("fade_seconds", 4.0))
        volume = float(theme_cfg.get("volume", 0.7))
        # Sting plays alone for the lead, then fades out under the open.
        filters.append(
            f"[{index}:a]atrim=0:{theme_lead + fade},volume={volume},"
            f"afade=t=out:st={theme_lead}:d={fade}[theme]"
        )
        labels.append("[theme]")
        index += 1

    if ambience_file is not None:
        fade_out = min(3.0, ambience_seconds / 3)
        inputs += ["-i", str(ambience_file)]
        filters.append(
            f"[{index}:a]volume={ambience_volume},afade=t=in:d=1.5,"
            f"afade=t=out:st={ambience_seconds - fade_out}:d={fade_out}[amb]"
        )
        labels.append("[amb]")
        index += 1

    for i, (path, start, featured, seconds) in enumerate(sfx_placements):
        inputs += ["-i", str(path)]
        # Fade in, and fade the tail out so it dissolves rather than cutting.
        tail = min(1.2 if featured else 1.0, seconds / 3)
        fade_out_st = max(0.0, seconds - tail)
        stages = []
        if featured:
            # Full in the clear for the spotlight, then duck as the voice
            # returns (ramp starts a touch early so speech never lands on a
            # loud transient) and ride quietly underneath.
            duck_at = max(0.4, spotlight_seconds - 0.2)
            ramp = 0.5
            expr = (
                f"if(lt(t,{duck_at}),{feature_volume},"
                f"if(lt(t,{duck_at}+{ramp}),"
                f"{feature_volume}+({duck_volume}-{feature_volume})*(t-{duck_at})/{ramp},"
                f"{duck_volume}))"
            ).replace(",", "\\,")
            stages.append(f"volume={expr}:eval=frame")
        else:
            stages.append(f"volume={effect_volume}")
        stages.append("afade=t=in:d=0.4")
        stages.append(f"afade=t=out:st={fade_out_st:.2f}:d={tail:.2f}")
        stages.append(f"adelay=delays={int(start * 1000)}:all=1")
        filters.append(f"[{index}:a]{','.join(stages)}[sfx{i}]")
        labels.append(f"[sfx{i}]")
        index += 1

    chain = f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0"
    if normalize:
        chain += ",loudnorm=I=-16:TP=-1.5:LRA=13"
    filters.append(chain + "[out]")

    cmd = [
        "ffmpeg",
        *inputs,
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[out]",
        "-ar",
        "44100",
        "-b:a",
        "192k",
        "-y",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mix failed: {result.stderr.decode()[-500:]}")
