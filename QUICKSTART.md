# Vibecast Quickstart

Get your personalized podcast running in ~10 minutes.

> **📌 Note:** This repo is both the source code and the maintainer's personal podcast. Before deploying, you'll customize it to be YOUR podcast. The setup process guides you through this!

## Step 1: Fork & Clone (2 min)

1. **Fork** this repository on GitHub (click "Fork" button)
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/vibecast.git
   cd vibecast
   ```
3. **Update the config** (important!):
   - Edit `podcast/config.yaml`
   - Change `author:` to your name
   - Change `github_url:` to point to your fork
   - Set your location (or use environment variables)

## Step 2: Set Up Cloudflare R2 (3 min)

**Why R2?** Free 10GB storage for audio files and transcripts.

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/) → **R2**
2. **Create bucket**: Name it `vibecast` (or anything you want)
3. **Enable public access**:
   - Click your bucket → Settings
   - Under "Public access", click **Allow Access**
   - Copy the **R2.dev subdomain** (e.g., `pub-xxxxx.r2.dev`)
4. **Create API token**:
   - R2 → Manage R2 API Tokens → Create API Token
   - Permissions: **Object Read & Write**
   - Copy the **Access Key ID** and **Secret Access Key**

## Step 3: Configure GitHub Secrets (3 min)

Go to your forked repo → **Settings → Secrets and variables → Actions** → **New repository secret**

Add these secrets:

| Secret Name | Where to Find It |
|------------|------------------|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `R2_ACCOUNT_ID` | Cloudflare Dashboard → R2 (top of page) |
| `R2_ACCESS_KEY_ID` | From Step 2 |
| `R2_SECRET_ACCESS_KEY` | From Step 2 |

**Optional but recommended:**

| Secret Name | Example Value |
|------------|---------------|
| `VIBECAST_LOCATION_NAME` | `Portland, OR` |
| `VIBECAST_LOCATION_LAT` | `45.5152` |
| `VIBECAST_LOCATION_LON` | `-122.6784` |
| `VIBECAST_AUTHOR` | `Your Name` |
| `VIBECAST_OWNER_EMAIL` | `you@example.com` |
| `VIBECAST_R2_PUBLIC_URL` | `https://pub-xxxxx.r2.dev` (from Step 2) |

## Step 4: Enable GitHub Pages (1 min)

1. Go to **Settings → Pages**
2. **Source**: Deploy from a branch
3. **Branch**: `main`, folder: `/docs`
4. Click **Save**

GitHub will give you a URL like: `https://YOUR_USERNAME.github.io/vibecast/`

## Step 5: Run Your First Episode! (1 min)

1. Go to **Actions** tab
2. Click **Daily Podcast** workflow
3. Click **Run workflow** → **Run workflow**
4. Wait ~2 minutes for it to complete

## Step 6: Subscribe to Your Podcast

After the workflow completes:

1. Visit: `https://YOUR_USERNAME.github.io/vibecast/`
2. Click the **RSS** button to copy your feed URL
3. Paste it in your podcast app (Apple Podcasts, Overcast, Pocket Casts, etc.)

🎉 **You're done!** Your podcast will update daily at 4:00 AM UTC (configure this in `.github/workflows/daily.yml`).

---

## Customize Your Vibe

Edit `podcast/config.yaml` to change:

- **Mood & personality** (calm, energetic, witty, etc.)
- **Voice** (6 OpenAI voices or 29+ ElevenLabs voices)
- **Topics** (embrace/avoid certain subjects)
- **Sources** (add your favorite RSS feeds)

See full customization options in [README.md](README.md).

## Local Development (Optional)

Want to test locally before committing?

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values

# Check your configuration
python check_config.py

# Dry run (no API calls, free!)
python -m podcast.run_daily --dry-run -v

# Real run (costs ~$0.05)
python -m podcast.run_daily -v
```

**Pro tip:** Run `python check_config.py` before your first real run to make sure everything is configured correctly!

## Troubleshooting

**GitHub Action fails:**
- Check that all required secrets are set
- Look at the Actions logs for specific errors
- Try running with `dry_run: true` first

**No audio in episode:**
- Verify R2_PUBLIC_URL is correct
- Check R2 bucket has public access enabled
- Ensure API keys are valid

**Bad voice quality:**
- Enable audio processing in `config.yaml` (under `tts.audio_processing`)
- Try different presets: `clarity`, `warmth`, or `podcast`
- See `AUDIO_PROCESSING_GUIDE.md` for details

## Need Help?

- **Check the full [README.md](README.md)** for detailed docs
- **Open an issue** if something's broken
- **Start a discussion** for questions or ideas

## What's Next?

- Change the vibe in `config.yaml`
- Add your favorite RSS sources
- Customize the schedule in `.github/workflows/daily.yml`
- Share your podcast! We'd love to hear it

