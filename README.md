# Vibecast

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**Your personalized AI podcast, generated daily and tailored to your vibe.**

Vibecast is an open-source podcast generator that creates daily audio briefings from your favorite news sources. Configure the mood, voice, topics, and sources—then let GitHub Actions automatically generate and publish episodes every day.

**[📚 Quickstart Guide](QUICKSTART.md)** · **[🤝 Contributing](CONTRIBUTING.md)** 

---

> **⚠️ Note for Cloners:** This repository is both the source code AND my personal podcast. Before deploying, update `podcast/config.yaml` with your own name, email, and preferences. See [Quickstart Guide](QUICKSTART.md) for setup.

---

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
- **Dual TTS providers** — OpenAI (default) or ElevenLabs, switchable via config
- **Professional audio processing** — FFmpeg-based enhancement removes "tin-can" sound
- **Multiple voices** — 6 OpenAI voices or 29+ ElevenLabs voices
- **Smart filtering** — Block negative keywords, boost positive ones
- **Source diversity** — Ensures variety across RSS feeds
- **Deduplication** — Won't repeat stories within 7 days
- **Transcripts** — Full script + references saved for each episode
- **NASA episode artwork** — Each episode gets a NASA image (APOD or Image Library)
- **Config-driven site** — Landing page regenerates from config
- **Zero server costs** — Runs on GitHub Actions free tier

## Quick Start

**Want to jump right in?** Follow the **[📚 10-Minute Quickstart Guide](QUICKSTART.md)**

Or read the detailed setup below:

### 1. Fork this repository

Click "Fork" on GitHub, then clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/vibecast.git
cd vibecast
```

### 2. Customize your podcast

**⚠️ Important:** Update these in `podcast/config.yaml` before deploying:

```yaml
podcast:
  title: "Your Podcast Name"  # Change this!
  author: "Your Name"          # Change this!
  github_url: "https://github.com/YOUR_USERNAME/vibecast"  # Change this!

location:
  name: "Your City"   # For weather
  lat: 0.0           # Your latitude
  lon: 0.0           # Your longitude
```

Or use environment variables (recommended for privacy):
- `VIBECAST_AUTHOR`
- `VIBECAST_LOCATION_NAME`, `VIBECAST_LOCATION_LAT`, `VIBECAST_LOCATION_LON`

### 3. Set up Cloudflare R2

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

**Optional:**

| Secret | Description |
|--------|-------------|
| `ELEVENLABS_API_KEY` | ElevenLabs API key (only if using ElevenLabs TTS) |

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

### Choose TTS Provider & Voice

**OpenAI TTS** (Default):
```yaml
tts:
  provider: "openai"
  openai:
    model: "tts-1-hd"  # tts-1 or tts-1-hd
    voice: "nova"       # alloy, echo, fable, onyx, nova, shimmer
    speed: 0.95         # 0.25 to 4.0
  audio_processing:
    enabled: true
    preset: "clarity"   # Removes "tin-can" sound
```

| Voice | Character |
|-------|-----------|
| `nova` | Friendly, warm — great for upbeat content |
| `shimmer` | Soft, gentle — ideal for calm/meditative |
| `echo` | Warm, conversational male |
| `fable` | Expressive, storyteller |
| `onyx` | Deep, authoritative male |
| `alloy` | Neutral, balanced |

**ElevenLabs** (Optional, requires API key):
```yaml
tts:
  provider: "elevenlabs"
  elevenlabs:
    voice_id: "rachel"                    # or emily, josh, adam, etc.
    model_id: "eleven_turbo_v2_5"         # or eleven_multilingual_v2
    stability: 0.5
    similarity_boost: 0.75
```

See `AUDIO_PROCESSING_GUIDE.md` for details on audio enhancement presets.

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
│   ├── config.yaml           # Vibe configuration
│   ├── run_daily.py          # Main orchestrator
│   ├── sources/              # Content fetchers
│   │   ├── weather.py        # Open-Meteo API
│   │   ├── rss.py            # RSS feed parser
│   │   ├── api.py            # Generic API (extensible)
│   │   └── images/           # Episode artwork providers
│   │       ├── base.py       # Provider interface
│   │       └── nasa.py       # NASA APOD + Image Library
│   ├── writer.py             # AI script generation
│   ├── tts/                  # TTS providers (pluggable)
│   │   ├── __init__.py       # Factory & preprocessing
│   │   ├── base.py           # Provider interface
│   │   ├── openai_tts.py    # OpenAI TTS (default)
│   │   └── elevenlabs.py    # ElevenLabs TTS (optional)
│   ├── audio_processing.py   # FFmpeg audio enhancement
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

## Example Configurations

Check out the `examples/` directory for inspiration:

- **`calm-morning.yaml`** — Gentle, mindful podcast for peaceful mornings
- **`energetic-commute.yaml`** — High-energy content for workouts (coming soon)
- **`tech-focused.yaml`** — Developer and tech enthusiast focused (coming soon)

Copy an example to `podcast/config.yaml` and customize it for your needs!

## Contributing

We welcome contributions! Whether it's:
- 🐛 Bug fixes
- ✨ New features
- 📚 Documentation improvements  
- 🎨 Example configurations
- 💡 Ideas and feedback

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for guidelines.

### Share Your Podcast!

Created something cool with Vibecast? We'd love to hear about it! Share in **[Discussions](../../discussions)**.

## Troubleshooting

**Common Issues:**

- **"No module named 'yaml'"** — Run `pip install -r requirements.txt`
- **"Permission denied" on R2** — Check your R2 credentials and bucket permissions
- **"Low audio quality"** — Enable `audio_processing` in config and try the `clarity` preset
- **"GitHub Action fails"** — Verify all secrets are set correctly

See [QUICKSTART.md](QUICKSTART.md#troubleshooting) for more help.

## Roadmap

- [ ] Web UI for config editing
- [ ] More TTS provider options (Azure, Google Cloud)
- [ ] Multi-language support
- [ ] Scheduled episode variations (weekend vs weekday)
- [ ] Integration with more content sources (YouTube, Substack, etc.)

Have ideas? **[Open a discussion](../../discussions)**!

## License

MIT © [Dominic Critchlow](https://github.com/domcritchlow)

## Acknowledgments

Vibecast is built with:
- **[OpenAI](https://openai.com/)** — GPT-4 for script generation, TTS for voices
- **[Cloudflare R2](https://www.cloudflare.com/products/r2/)** — Free object storage
- **[GitHub Actions](https://github.com/features/actions)** — Free automation
- **[GitHub Pages](https://pages.github.com/)** — Free hosting
- **[FFmpeg](https://ffmpeg.org/)** — Audio processing

Special thanks to all the RSS sources providing positive news feeds!

---

**Made something cool with Vibecast? [⭐ Star this repo](../../stargazers) and [share your podcast](../../discussions)!**
