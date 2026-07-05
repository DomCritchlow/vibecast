"""Tests for the special-episode production pipeline (no API calls, no ffmpeg)."""

from datetime import datetime
from pathlib import Path

from podcast.production import (
    AMBIENCE_SUFFIX,
    ScriptPart,
    _record_in_library_index,
    build_timeline,
    is_special_episode,
    load_library_index,
    parse_ambience_cue,
    parse_script_cues,
    sfx_library_dir,
    sfx_library_path,
    specials_this_week,
    strip_sfx_cues,
    weather_ambience_prompt,
)
from podcast.writer import build_system_prompt, clean_script_for_tts

CONFIG = {
    "vibe": {"voice_persona": {"name": "Testo"}},
    "podcast": {"title": "Testcast"},
    "episode": {"target_minutes": 4},
    "tts": {
        "provider": "openai",
        "special_episodes": {
            "enabled": True,
            "provider": "fal",
            "weekly_budget": 1,
            "quality_gate": {"enabled": True, "threshold": 0.8},
            "fallback_day": "friday",
            "sound_design": {"max_effects": 3},
        },
    },
}

# A week with no specials produced yet.
EMPTY_STATE = {"special_dates": []}
FRIDAY = datetime(2026, 7, 3)
MONDAY = datetime(2026, 6, 29)  # same ISO week as FRIDAY

SCRIPT = """[AMBIENCE: gentle rain over a quiet street, a distant subway rumble]

So here's the thing about rockets. [excited] They came back.

[SFX: distant rocket launch rumble]

The booster landed on the same pad it left from, eight minutes later.

[SFX: quiet trading floor murmur]

Meanwhile the markets barely noticed."""


# --- scheduling ---


def test_fallback_day_fires_when_budget_unspent():
    # Friday is the use-it-or-lose-it day; a plain weekday is not.
    assert is_special_episode(CONFIG, FRIDAY, state=EMPTY_STATE)
    assert not is_special_episode(CONFIG, MONDAY, state=EMPTY_STATE)


def test_quality_gate_promotes_standout_weekday():
    # A high score promotes an ordinary weekday; a mediocre one does not.
    assert is_special_episode(CONFIG, MONDAY, state=EMPTY_STATE, quality_score=0.9)
    assert not is_special_episode(CONFIG, MONDAY, state=EMPTY_STATE, quality_score=0.5)


def test_weekly_budget_exhausted_skips_even_fallback_day():
    # A special already produced Tuesday -> Friday is skipped this week.
    state = {"special_dates": ["2026-06-30"]}  # same ISO week as FRIDAY
    assert not is_special_episode(CONFIG, FRIDAY, state=state)
    assert not is_special_episode(CONFIG, MONDAY, state=state, quality_score=0.99)


def test_budget_of_two_allows_a_second():
    config = {**CONFIG, "tts": {**CONFIG["tts"]}}
    config["tts"]["special_episodes"] = {**CONFIG["tts"]["special_episodes"], "weekly_budget": 2}
    state = {"special_dates": ["2026-06-30"]}  # one used, one left
    assert is_special_episode(config, FRIDAY, state=state)


def test_special_respects_force_overrides():
    assert not is_special_episode(CONFIG, FRIDAY, state=EMPTY_STATE, force=False)
    assert is_special_episode(CONFIG, MONDAY, state=EMPTY_STATE, force=True)


def test_special_disabled_config():
    config = {"tts": {"special_episodes": {"enabled": False, "fallback_day": "friday"}}}
    assert not is_special_episode(config, FRIDAY, state=EMPTY_STATE)
    assert not is_special_episode({}, FRIDAY, state=EMPTY_STATE)


def test_specials_this_week_counts_only_current_iso_week():
    state = {
        "special_dates": [
            "2026-06-30",  # same ISO week as FRIDAY (2026-07-03)
            "2026-07-03",  # same week
            "2026-06-26",  # previous week
            "garbage",  # ignored
        ]
    }
    assert specials_this_week(state, FRIDAY) == 2
    assert specials_this_week({}, FRIDAY) == 0


# --- cue parsing ---


def test_parse_script_cues_alternates_voice_and_sfx():
    parts = parse_script_cues(SCRIPT)
    kinds = [p.kind for p in parts]
    assert kinds == ["voice", "sfx", "voice", "sfx", "voice"]
    assert parts[1].text == "distant rocket launch rumble"
    # Audio tags stay inside the voice text for the v3 engine
    assert "[excited]" in parts[0].text


def test_parse_script_cues_respects_max_effects():
    parts = parse_script_cues(SCRIPT, max_effects=1)
    assert [p.kind for p in parts].count("sfx") == 1
    # Voice on both sides of a dropped cue is preserved
    joined = " ".join(p.text for p in parts if p.kind == "voice")
    assert "markets barely noticed" in joined


def test_parse_script_cues_marks_featured_beat():
    script = (
        "Above the atmosphere.\n\n"
        "[SFX: distant rocket launch rumble | beat]\n\n"
        "The booster came home.\n\n"
        "[SFX: quiet trading floor murmur]\n\n"
        "Markets shrugged."
    )
    parts = parse_script_cues(script)
    sfx = [p for p in parts if p.kind == "sfx"]
    # The "| beat" modifier is stripped from the text and flips hold on
    assert sfx[0].text == "distant rocket launch rumble"
    assert sfx[0].hold is True
    # A plain cue stays under-voice texture
    assert sfx[1].text == "quiet trading floor murmur"
    assert sfx[1].hold is False


def test_parse_script_accepts_hold_synonym():
    parts = parse_script_cues("Hi.\n\n[SFX: thunderclap | hold]\n\nBye.")
    sfx = [p for p in parts if p.kind == "sfx"]
    assert sfx[0].text == "thunderclap"
    assert sfx[0].hold is True


def test_parse_script_ignores_inline_sfx_mentions():
    # Only standalone cue lines count; a bracket mid-sentence is voice text
    script = "He said [SFX: boom] is not a cue.\nStill talking."
    parts = parse_script_cues(script)
    assert [p.kind for p in parts] == ["voice"]


def test_strip_production_markup_leaves_plain_speech():
    from podcast.production import strip_production_markup

    plain = strip_production_markup(SCRIPT)
    assert "[" not in plain and "]" not in plain
    assert "So here's the thing about rockets. They came back." in plain
    assert "markets barely noticed" in plain


def test_strip_sfx_cues():
    stripped = strip_sfx_cues(SCRIPT)
    assert "[SFX:" not in stripped
    assert "[AMBIENCE:" not in stripped
    assert "rockets" in stripped and "markets barely noticed" in stripped


# --- timeline / featured beats ---


def _tl_parts():
    # voice, sfx(under), voice, sfx(beat), voice
    return [
        ScriptPart("voice", "one"),
        ScriptPart("sfx", "murmur", hold=False),
        ScriptPart("voice", "two"),
        ScriptPart("sfx", "rocket", hold=True),
        ScriptPart("voice", "three"),
    ]


def test_build_timeline_beat_shifts_later_voice(tmp_path):
    parts = _tl_parts()
    vf = [tmp_path / "v0.mp3", tmp_path / "v1.mp3", tmp_path / "v2.mp3"]
    durations = [5.0, 5.0, 5.0]
    generated = {
        1: (tmp_path / "sfx-under.mp3", 5.0),
        3: (tmp_path / "sfx-beat.mp3", 3.0),
    }
    voices, sfx = build_timeline(
        parts, vf, durations, generated, theme_lead=2.0, spotlight_seconds=2.0, lead_seconds=0.5
    )

    # Voice starts: v0 at theme_lead=2; v1 at 7; v2 after the pause (lead 0.5 +
    # spotlight 2.0) following v1's end at 12 -> 14.5. The sound's own length
    # (3s) does NOT extend the pause; its tail rides under v2.
    assert [start for _, start, _ in voices] == [2.0, 7.0, 14.5]
    # Only the voice resuming after the spotlight is flagged for a fade-in
    assert [fade for _, _, fade in voices] == [False, False, True]

    # Under-voice effect sits at its cue (after v0): 2 + 5 = 7, no lead breath
    assert sfx[0] == (tmp_path / "sfx-under.mp3", 7.0, False, 5.0)
    # Featured effect starts after v1 (7 + 5 = 12) plus a 0.5s lead breath = 12.5
    assert sfx[1] == (tmp_path / "sfx-beat.mp3", 12.5, True, 3.0)


def test_build_timeline_failed_effect_adds_no_beat(tmp_path):
    parts = _tl_parts()
    vf = [tmp_path / "v0.mp3", tmp_path / "v1.mp3", tmp_path / "v2.mp3"]
    durations = [5.0, 5.0, 5.0]
    # The featured (beat) effect at index 3 failed to generate -> not present.
    generated = {1: (tmp_path / "sfx-under.mp3", 5.0)}
    voices, sfx = build_timeline(
        parts, vf, durations, generated, theme_lead=0.0, spotlight_seconds=2.0, lead_seconds=0.5
    )

    # The featured effect failed, so no pause: v2 starts at 10 (0 + 5 + 5), not later
    assert [start for _, start, _ in voices] == [0.0, 5.0, 10.0]
    # No spotlight happened, so no voice gets a fade-in
    assert not any(fade for _, _, fade in voices)
    assert len(sfx) == 1


# --- ambience ---


def test_parse_ambience_cue_extracts_direction():
    direction, remaining = parse_ambience_cue(SCRIPT)
    assert direction == "gentle rain over a quiet street, a distant subway rumble"
    assert "[AMBIENCE:" not in remaining
    assert remaining.startswith("So here's the thing about rockets.")


def test_parse_ambience_cue_absent():
    direction, remaining = parse_ambience_cue("Just talking.\nNo cues here.")
    assert direction is None
    assert remaining == "Just talking.\nNo cues here."


def test_weather_ambience_matches_conditions():
    assert "rain" in weather_ambience_prompt("Light rain this morning, 62F")
    assert "snow" in weather_ambience_prompt("Snow flurries expected")
    assert "birds" in weather_ambience_prompt("Clear and sunny, 75F")


def test_weather_ambience_fallback():
    prompt = weather_ambience_prompt("Weather information is not available today.")
    assert "ambience" in prompt


# --- sound library ---


def test_sfx_library_path_is_deterministic_and_readable():
    lib = Path("/lib")
    a = sfx_library_path(lib, "Distant rocket launch rumble!", 5.0, False)
    b = sfx_library_path(lib, "Distant rocket launch rumble!", 5.0, False)
    assert a == b
    assert a.name.startswith("distant-rocket-launch-rumble--5s-")
    assert a.suffix == ".mp3"


def test_sfx_library_path_distinguishes_requests():
    lib = Path("/lib")
    base = sfx_library_path(lib, "rain on a city street", 15.0, True)
    assert "-loop-" in base.name
    assert base != sfx_library_path(lib, "rain on a city street", 15.0, False)
    assert base != sfx_library_path(lib, "rain on a city street", 10.0, True)


def test_sfx_library_dir_respects_toggle():
    assert sfx_library_dir({"library": False}) is None
    default_dir = sfx_library_dir({})
    assert default_dir is not None and default_dir.name == "sfx"


def test_library_index_round_trip(tmp_path):
    assert load_library_index(tmp_path) == []
    _record_in_library_index(
        tmp_path, "rain--15s-loop-abc.mp3", f"rain on glass{AMBIENCE_SUFFIX}", 15.0, True
    )
    _record_in_library_index(tmp_path, "rumble--5s-def.mp3", "distant rumble", 5.0, False)

    entries = load_library_index(tmp_path)
    assert len(entries) == 2
    bed = next(e for e in entries if e["loop"])
    # The shelf shows the bare direction the writer would reuse verbatim
    assert bed["direction"] == "rain on glass"
    assert bed["prompt"].endswith(AMBIENCE_SUFFIX)

    # Re-recording the same file replaces, not duplicates
    _record_in_library_index(
        tmp_path, "rain--15s-loop-abc.mp3", f"rain on glass{AMBIENCE_SUFFIX}", 15.0, True
    )
    assert len(load_library_index(tmp_path)) == 2


def test_library_index_ignores_missing_or_corrupt(tmp_path):
    assert load_library_index(None) == []
    (tmp_path / "index.json").write_text("not json{")
    assert load_library_index(tmp_path) == []


def test_shelf_appears_in_production_prompt(tmp_path):
    _record_in_library_index(
        tmp_path, "rain--15s-loop-abc.mp3", f"rain on glass{AMBIENCE_SUFFIX}", 15.0, True
    )
    config = {
        **CONFIG,
        "tts": {
            "provider": "openai",
            "special_episodes": {
                "enabled": True,
                "fallback_day": "friday",
                "sound_design": {"max_effects": 3, "library_dir": str(tmp_path)},
            },
        },
    }
    prompt = build_system_prompt(config, special=True)
    assert "THE SHELF" in prompt
    assert "- rain on glass" in prompt

    # Empty library -> no shelf section
    empty = tmp_path / "empty"
    config["tts"]["special_episodes"]["sound_design"]["library_dir"] = str(empty)
    assert "THE SHELF" not in build_system_prompt(config, special=True)


# --- writer integration ---


def test_special_prompt_includes_production_section():
    normal = build_system_prompt(CONFIG)
    special = build_system_prompt(CONFIG, special=True)
    assert "AUDIO PRODUCTION" not in normal
    assert "AUDIO PRODUCTION" in special
    assert "up to 3 sound-effect cues" in special


def test_clean_script_keeps_cues_for_special():
    cleaned = clean_script_for_tts(SCRIPT, keep_production_cues=True)
    assert "[SFX: distant rocket launch rumble]" in cleaned
    assert "[excited]" in cleaned


def test_clean_script_strips_cues_for_normal():
    cleaned = clean_script_for_tts(SCRIPT)
    assert "[SFX:" not in cleaned
    assert "[AMBIENCE:" not in cleaned
    assert "markets barely noticed" in cleaned
