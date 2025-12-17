# Vibecast

A configurable daily podcast engine that generates personalized audio briefings with weather and positive news.

Vibecast runs automatically via GitHub Actions, gathers uplifting content from RSS feeds, writes a script using AI, converts it to speech, and publishes it as a podcast you can subscribe to in any podcast app.

## How It Works

```
RSS Feeds + Weather API
        │
        ▼
   Filter & Select
        │
        ▼
   GPT-4o-mini ──► Script
        │
        ▼
   OpenAI TTS ──► MP3
        │
        ├──► Cloudflare R2 (audio hosting)
        └──► GitHub Pages (RSS feed)
```

Every day at your scheduled time:

1. **Gather** — Fetches weather and positive news from RSS feeds
2. **Filter** — Removes negative content, prioritizes uplifting stories
3. **Write** — AI generates a ~4 minute script matching your vibe
4. **Speak** — Text-to-speech creates an MP3
5. **Publish** — Uploads audio, updates RSS feed, regenerates landing page

## Features

- **Vibe-configurable** — Change the entire personality via `config.yaml`
- **Multiple voices** — Choose from 6 OpenAI TTS voices
- **Smart filtering** — Block negative keywords, boost positive ones
- **Source diversity** — Ensures variety across RSS feeds
- **Deduplication** — Won't repeat stories within 7 days
- **Transcripts** — Full script + references saved for each episode
- **NASA episode artwork** — Each episode gets a NASA image (APOD or Image Library)
- **Config-driven site** — Landing page regenerates from config
- **Zero server costs** — Runs on GitHub Actions free tier

## Quick Start

### 1. Fork this repository

### 2. Set up Cloudflare R2

1. Create an R2 bucket (e.g., `vibecast`)
2. Enable public access via R2.dev subdomain
3. Create an API token with read/write permissions

### 3. Add GitHub Secrets

Go to **Settings → Secrets → Actions** and add:

**Required:**

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `R2_ACCOUNT_ID` | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | R2 API access key |
| `R2_SECRET_ACCESS_KEY` | R2 API secret key |

**Personal settings:**

| Secret | Example |
|--------|---------|
| `VIBECAST_LOCATION_NAME` | `New York, NY` |
| `VIBECAST_LOCATION_LAT` | `40.7128` |
| `VIBECAST_LOCATION_LON` | `-74.0060` |
| `VIBECAST_SITE_URL` | `https://user.github.io/vibecast/` |
| `VIBECAST_FEED_URL` | `https://user.github.io/vibecast/feed.xml` |
| `VIBECAST_R2_PUBLIC_URL` | `https://pub-xxx.r2.dev` |
| `VIBECAST_AUTHOR` | `Your Name` |
| `VIBECAST_AUTHOR_URL` | `https://yoursite.com` |
| `VIBECAST_OWNER_EMAIL` | `you@example.com` |
| `VIBECAST_ARTWORK_URL` | `https://user.github.io/vibecast/artwork.png` |

### 4. Enable GitHub Pages

**Settings → Pages → Source:** `main` branch, `/docs` folder

### 5. Run it

**Actions → Daily Podcast → Run workflow**

## Customization

### Change the Vibe

Edit `podcast/config.yaml`:

```yaml
vibe:
  name: "Morning Sunshine"
  mood:
    primary: "calm"
    secondary: "optimistic"
    energy: "gentle-lift"
  
  voice_persona:
    name: "A warm morning companion"
    personality:
      - "speaks like a friend who's genuinely happy to see you"
      - "finds wonder in small things"
```

### Choose a Voice

```yaml
openai:
  tts:
    voice: "nova"    # alloy, echo, fable, onyx, nova, shimmer
    speed: 0.95      # 0.25 to 4.0
```

| Voice | Character |
|-------|-----------|
| `nova` | Friendly, warm — great for upbeat content |
| `shimmer` | Soft, gentle — ideal for calm/meditative |
| `echo` | Warm, conversational male |
| `fable` | Expressive, storyteller |
| `onyx` | Deep, authoritative male |
| `alloy` | Neutral, balanced |

### Add RSS Sources

```yaml
sources:
  rss:
    - name: "Good News Network"
      url: "https://www.goodnewsnetwork.org/feed/"
      enabled: true
      max_items: 3
      trust_score: 0.9
```

## Project Structure

```
vibecast/
├── podcast/
│   ├── config.yaml        # Vibe configuration
│   ├── run_daily.py       # Main orchestrator
│   ├── sources/           # Content fetchers
│   │   ├── weather.py     # Open-Meteo API
│   │   ├── rss.py         # RSS feed parser
│   │   ├── nasa_apod.py   # NASA images for episode art
│   │   └── api.py         # Generic API (extensible)
│   ├── writer.py          # AI script generation
│   ├── tts.py             # OpenAI TTS synthesis
│   ├── storage.py         # R2 upload
│   ├── rss_feed.py        # Podcast RSS generation
│   └── site_generator.py  # Landing page generator
├── docs/
│   ├── index.html         # Landing page (auto-generated)
│   ├── feed.xml           # Podcast RSS feed
│   ├── scripts/           # Episode transcripts
│   └── artwork.png        # Podcast artwork
└── .github/workflows/
    └── daily.yml          # GitHub Actions cron job
```

## Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your values

# Run dry-run (no API costs)
source .env
python -m podcast.run_daily --dry-run -v

# Run for real
python -m podcast.run_daily -v
```

## Cost

| Service | Cost |
|---------|------|
| GitHub Actions | Free |
| GitHub Pages | Free |
| Cloudflare R2 | Free tier (10GB) |
| OpenAI GPT-4o-mini | ~$0.01-0.02/episode |
| OpenAI TTS | ~$0.03-0.10/episode |

**Total: ~$1.50-4.50/month** for daily episodes

## License

MIT
