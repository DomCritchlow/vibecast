# Telegram Episode Notifications

About an hour after each episode publishes, **Bento reaches out to you directly
on Telegram**: the episode's risograph artwork as a photo card, a short personal
note about what hooked him in today's episode, and buttons that jump straight
into your podcast player.

```
┌─────────────────────────────────┐
│  [episode artwork]              │
│                                 │
│  **Fusion Milestone & Ocean    │
│  Mapping Update**               │
│                                 │
│  Someone just mapped a chunk    │
│  of the Pacific floor nobody    │
│  had ever seen — and the AI     │
│  angle is wilder than the map.  │
│  It's 4:25, good walk length.   │
│                                 │
│  4:25 · 6 stories · Friday,     │
│  July 4                         │
│  ┌───────────────────────────┐  │
│  │   🎧 Listen in Overcast   │  │
│  ├─────────────┬─────────────┤  │
│  │ 🗞️ The paper │ 📄 Transcript│  │
│  └─────────────┴─────────────┘  │
└─────────────────────────────────┘
```

## How it works

1. `daily.yml` publishes the episode at 09:00 UTC as usual.
2. One hour later, `notify-telegram.yml` (cron 10:00 UTC) runs
   `python -m podcast.notify`, which:
   - loads the latest episode JSON,
   - has the writer LLM (same one that writes the show) draft a 2–3 sentence
     note in Bento's voice — with a plain template fallback if no API key is
     available,
   - sends a `sendPhoto` card to your chat with the episode art, the note,
     and inline buttons,
   - stamps `notifications.telegram.sent_at` into the episode JSON and
     commits it, so reruns never double-send.
3. If the daily run failed that morning, the notifier notices the latest
   episode is older than `max_age_hours` and stays quiet.

## Setup (5 minutes)

### 1. Create the bot

1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → pick a name
   (e.g. "Bento") and a username.
2. Copy the bot token it gives you.

### 2. Get your chat id

1. Send your new bot any message (it can't message you first).
2. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser
   and read `message.chat.id` — or message
   [@userinfobot](https://t.me/userinfobot) for your id.

### 3. Add repository secrets

In GitHub → Settings → Secrets and variables → Actions:

| Secret | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | token from @BotFather |
| `TELEGRAM_CHAT_ID` | your chat id |

(For local testing, put the same two values in `.env`.)

### 4. Done

The workflow is already scheduled. Test it immediately from the Actions tab:
**Telegram Notification → Run workflow** (set `force: true` to resend today's
episode, or `dry_run: true` to see the message in the logs without sending).

Local test:

```bash
uv run python -m podcast.notify --dry-run -v          # print, don't send
uv run python -m podcast.notify --force -v            # actually send latest
uv run python -m podcast.notify --date 2026-07-04 -v  # send a specific episode
```

## The Overcast button

Telegram buttons only accept `https://` URLs, but Overcast's app deep link is
a custom `overcast://` scheme. The button therefore points at the site's
**`listen.html`** hand-off page, which immediately bounces Apple devices into
the Overcast app (`overcast://x-callback-url/add?url=<feed>` — for an
already-subscribed feed this opens the show page, with today's episode on
top). Non-Apple devices see fallback options: web player and copy-feed-URL.

Two nicer options if they apply to you, in `podcast/config.yaml`:

```yaml
notifications:
  telegram:
    # If your show is listed in Apple Podcasts, this links straight to
    # Overcast's own page for it (opens the app, no hand-off hop):
    apple_podcast_id: "1234567890"

    # Or point the button anywhere you like:
    listen_url: "https://overcast.fm/+yourEpisodePage"
```

## Configuration reference

Everything lives under `notifications.telegram` in `podcast/config.yaml`:

| Key | Default | What it does |
|---|---|---|
| `enabled` | `true` | Master switch (secrets missing = fails the workflow run) |
| `personal_note` | `true` | Bento writes a fresh note via the writer LLM |
| `max_note_chars` | `400` | Keeps the note text-message sized |
| `max_age_hours` | `36` | Never announce an episode older than this |
| `listen_url` | `""` | Explicit listen button URL (overrides everything) |
| `apple_podcast_id` | `""` | Use `https://overcast.fm/itunes<id>` for the button |
| `buttons.newspaper` | `true` | Show the 🗞️ paper button |
| `buttons.transcript` | `true` | Show the 📄 transcript button |
