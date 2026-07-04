"""Telegram episode notifications — Bento pings you when a new episode drops.

Runs as a separate step about an hour after the daily pipeline publishes an
episode (see .github/workflows/notify-telegram.yml). Sends a photo card to a
Telegram chat: the episode's risograph artwork, a short personal note written
by Bento via the configured writer LLM, and inline buttons that deep-link
into Overcast (via the site's listen.html hand-off page), the newspaper PDF,
and the transcript.

Credentials come from the environment only (never config.yaml):

    TELEGRAM_BOT_TOKEN   from @BotFather
    TELEGRAM_CHAT_ID     your chat with the bot (or a channel/group id)

Behavior knobs live in config.yaml under notifications.telegram.

Each successful send stamps notifications.telegram.sent_at into the episode
JSON, so reruns of the workflow are no-ops unless --force is passed.
"""

import argparse
import html
import json
import logging
import os
import sys
from datetime import datetime, timedelta

import httpx

from .episode_store import get_latest_episode, load_episode, save_episode
from .run_daily import load_config
from .writer import get_writer

logger = logging.getLogger("vibecast.notify")

TELEGRAM_API_BASE = "https://api.telegram.org"

# Telegram hard limits
CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096

DEFAULT_MAX_AGE_HOURS = 36
DEFAULT_MAX_NOTE_CHARS = 400


class NotifyError(RuntimeError):
    """A notification step failed in a way that should fail the run."""


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def telegram_config(config: dict) -> dict:
    return (config.get("notifications") or {}).get("telegram") or {}


def resolve_listen_url(config: dict) -> str:
    """Pick the URL for the primary "listen" button.

    Priority:
      1. notifications.telegram.listen_url — explicit override
      2. notifications.telegram.apple_podcast_id — https://overcast.fm/itunes<id>,
         a universal link that opens the show directly in the Overcast app
      3. <site_url>/listen.html — the site's hand-off page, which redirects
         into Overcast via its overcast:// URL scheme (Telegram buttons only
         accept http(s) URLs, so the custom scheme needs an https hop)
    """
    tg = telegram_config(config)

    if tg.get("listen_url"):
        return tg["listen_url"]

    apple_id = str(tg.get("apple_podcast_id") or "").strip()
    if apple_id:
        return f"https://overcast.fm/itunes{apple_id}"

    site_url = (config.get("podcast") or {}).get("site_url", "").rstrip("/")
    if not site_url:
        raise NotifyError(
            "Cannot build listen URL: set podcast.site_url or notifications.telegram.listen_url"
        )
    return f"{site_url}/listen.html"


# ---------------------------------------------------------------------------
# Message composition
# ---------------------------------------------------------------------------


def _episode_date_pretty(episode: dict) -> str:
    try:
        return datetime.fromisoformat(episode["date"]).strftime("%A, %B %-d")
    except (KeyError, ValueError):
        return episode.get("guid", "")


def fallback_note(episode: dict, config: dict) -> str:
    """Deterministic Bento note used when the writer LLM is unavailable."""
    persona = (config.get("vibe") or {}).get("voice_persona") or {}
    name = persona.get("name", "Bento")
    stories = episode.get("stories") or []
    hook = f" The one that got me: {stories[0]['title'].rstrip('.')}." if stories else ""
    duration = episode.get("duration_formatted") or ""
    length = f" It's {duration} — a good coffee's worth." if duration else ""
    return f"Morning, it's {name}. Today's episode is up.{hook}{length}"


def compose_bento_note(episode: dict, config: dict) -> str:
    """Have the writer LLM draft a short personal note in Bento's voice.

    Falls back to a deterministic template on any failure so the
    notification never dies on a missing key or API hiccup.
    """
    tg = telegram_config(config)
    max_chars = int(tg.get("max_note_chars", DEFAULT_MAX_NOTE_CHARS))

    if not tg.get("personal_note", True):
        return fallback_note(episode, config)

    vibe = config.get("vibe") or {}
    persona = vibe.get("voice_persona") or {}
    name = persona.get("name", "Bento")
    personality = "\n".join(f"- {p}" for p in persona.get("personality", []))

    stories_text = "\n".join(
        f"- {s['title']} ({s['source']}): {s.get('summary', '')[:200]}"
        for s in (episode.get("stories") or [])[:6]
    )

    system = f"""You are {name}, host of a short daily podcast. A new episode just \
went live and you're sending ONE short personal message to your one listener — a friend — \
to tell them it's ready. This is a text message, not ad copy.

PERSONALITY:
{personality}

RULES:
- 2 or 3 sentences, under {max_chars} characters total
- Lead with the thing that genuinely hooked you today — a specific detail, not a topic label
- Sound like a text from a friend: casual, contractions, no exclamation-point pileups
- No greetings like "Dear", no sign-off, no hashtags, no emoji, no links
- Plain text only — no markdown, no quotes around the whole thing
- Never use: shocking, you won't believe, crisis, game-changer"""

    user = f"""Episode title: {episode.get("title", "")}
Duration: {episode.get("duration_formatted", "")}
Today's stories:
{stories_text}

Write the message now."""

    try:
        writer = get_writer(config)
        logger.info("Composing Bento note with %s (%s)", writer.provider_name, writer.model)
        note = writer.generate_text(system, user, max_tokens=1000).strip().strip('"')
        if not note:
            raise ValueError("empty note")
        if len(note) > max_chars:
            note = note[: max_chars - 1].rsplit(" ", 1)[0] + "…"
        return note
    except Exception as e:
        logger.warning("Bento note generation failed (%s); using fallback note", e)
        return fallback_note(episode, config)


def build_caption(episode: dict, note: str) -> str:
    """Build the Telegram HTML caption: title, Bento's note, meta line."""
    title = html.escape(episode.get("title", "New episode"))
    meta_bits = [
        episode.get("duration_formatted") or "",
        f"{len(episode.get('stories') or [])} stories",
        _episode_date_pretty(episode),
    ]
    meta = " · ".join(bit for bit in meta_bits if bit)

    caption = f"<b>{title}</b>\n\n{html.escape(note)}\n\n<i>{html.escape(meta)}</i>"
    if len(caption) > CAPTION_LIMIT:
        # Trim the note, keep title and meta intact
        overflow = len(caption) - CAPTION_LIMIT + 1
        trimmed = html.escape(note)[: -(overflow)].rsplit(" ", 1)[0] + "…"
        caption = f"<b>{title}</b>\n\n{trimmed}\n\n<i>{html.escape(meta)}</i>"
    return caption


def build_reply_markup(episode: dict, config: dict) -> dict:
    """Inline keyboard: primary listen button, secondary paper/transcript row."""
    tg = telegram_config(config)
    buttons_config = tg.get("buttons") or {}
    media = episode.get("media") or {}

    rows = [[{"text": "🎧 Listen in Overcast", "url": resolve_listen_url(config)}]]

    second_row = []
    if buttons_config.get("newspaper", True) and media.get("newspaper_url"):
        second_row.append({"text": "🗞️ The paper", "url": media["newspaper_url"]})
    if buttons_config.get("transcript", True) and media.get("transcript_url"):
        second_row.append({"text": "📄 Transcript", "url": media["transcript_url"]})
    if second_row:
        rows.append(second_row)

    return {"inline_keyboard": rows}


# ---------------------------------------------------------------------------
# Telegram API
# ---------------------------------------------------------------------------


def _telegram_call(token: str, method: str, payload: dict) -> dict:
    response = httpx.post(f"{TELEGRAM_API_BASE}/bot{token}/{method}", data=payload, timeout=30)
    body = response.json()
    if not body.get("ok"):
        raise NotifyError(f"Telegram {method} failed: {body.get('description', response.text)}")
    return body


def send_episode_notification(episode: dict, config: dict, dry_run: bool = False) -> None:
    """Send the episode card to Telegram (photo with caption + buttons)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not dry_run and (not token or not chat_id):
        raise NotifyError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")

    note = fallback_note(episode, config) if dry_run else compose_bento_note(episode, config)
    caption = build_caption(episode, note)
    reply_markup = build_reply_markup(episode, config)

    media = episode.get("media") or {}
    artwork_url = media.get("artwork_url") or (config.get("podcast") or {}).get("artwork_url")

    if dry_run:
        logger.info("[DRY RUN] Would send to Telegram:")
        logger.info("[DRY RUN] photo: %s", artwork_url)
        logger.info("[DRY RUN] caption:\n%s", caption)
        logger.info("[DRY RUN] buttons: %s", json.dumps(reply_markup))
        return

    base_payload = {
        "chat_id": chat_id,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(reply_markup),
    }

    if artwork_url:
        try:
            _telegram_call(
                token, "sendPhoto", {**base_payload, "photo": artwork_url, "caption": caption}
            )
            logger.info("Sent photo notification")
            return
        except NotifyError as e:
            # Telegram fetches the photo server-side; if that fails (size,
            # timeout, content type) fall back to a text message with a
            # large link preview of the artwork instead of dying.
            logger.warning("%s; falling back to sendMessage", e)

    payload = {**base_payload, "text": caption[:MESSAGE_LIMIT]}
    if artwork_url:
        payload["link_preview_options"] = json.dumps(
            {"url": artwork_url, "prefer_large_media": True, "show_above_text": True}
        )
    _telegram_call(token, "sendMessage", payload)
    logger.info("Sent text notification")


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------


def already_notified(episode: dict) -> bool:
    return bool((episode.get("notifications") or {}).get("telegram", {}).get("sent_at"))


def mark_notified(episode: dict) -> None:
    episode.setdefault("notifications", {})["telegram"] = {
        "sent_at": datetime.now().isoformat()
    }
    save_episode(episode)


def episode_too_old(episode: dict, max_age_hours: float) -> bool:
    try:
        published = datetime.fromisoformat(episode["date"])
    except (KeyError, ValueError):
        return True
    return datetime.now() - published > timedelta(hours=max_age_hours)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(date: str | None = None, force: bool = False, dry_run: bool = False) -> bool:
    config = load_config()
    tg = telegram_config(config)

    if not tg.get("enabled", False) and not dry_run:
        logger.info("Telegram notifications disabled (notifications.telegram.enabled)")
        return True

    episode = load_episode(date) if date else get_latest_episode()
    if not episode:
        logger.warning("No episode found%s — nothing to send", f" for {date}" if date else "")
        return True

    if already_notified(episode) and not force:
        logger.info("Episode %s already notified — skipping", episode.get("guid"))
        return True

    # Guard the cron against announcing a stale episode on days the daily
    # pipeline failed. An explicit --date means the human knows what they want.
    max_age_hours = float(tg.get("max_age_hours", DEFAULT_MAX_AGE_HOURS))
    if not date and not force and episode_too_old(episode, max_age_hours):
        logger.info(
            "Latest episode %s is older than %sh — skipping (use --force to send anyway)",
            episode.get("guid"),
            max_age_hours,
        )
        return True

    try:
        send_episode_notification(episode, config, dry_run=dry_run)
    except NotifyError:
        logger.exception("Notification failed")
        return False

    if not dry_run:
        mark_notified(episode)
        logger.info("Marked %s as notified", episode.get("guid"))
    return True


def main():
    parser = argparse.ArgumentParser(description="Send the Telegram episode notification")
    parser.add_argument("--date", help="Episode date (YYYY-MM-DD); default: latest episode")
    parser.add_argument("--force", action="store_true", help="Send even if already notified")
    parser.add_argument(
        "--dry-run", action="store_true", help="Compose and print, but don't call Telegram"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-7s %(name)s: %(message)s",
    )
    for noisy in ("httpx", "httpcore", "anthropic", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    sys.exit(0 if run(date=args.date, force=args.force, dry_run=args.dry_run) else 1)


if __name__ == "__main__":
    main()
