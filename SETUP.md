# Vibecast Setup Guide

Complete setup instructions for Vibecast.

## Prerequisites

- GitHub account
- Cloudflare account (free tier)
- OpenAI API key with billing enabled

## 1. OpenAI API Setup

1. Go to [platform.openai.com](https://platform.openai.com/)
2. Navigate to **API Keys** → Create new key
3. Copy the key (starts with `sk-`)
4. Ensure billing is enabled

**Cost estimate:** ~$0.05-0.15 per episode

## 2. Cloudflare R2 Setup

### Create R2 Bucket

1. Log into [dash.cloudflare.com](https://dash.cloudflare.com/)
2. Go to **R2 Object Storage** in sidebar
3. Click **Create bucket**
4. Name: `vibecast`
5. Click **Create bucket**

### Enable Public Access

1. Go to bucket **Settings**
2. Under **Public access**, enable **R2.dev subdomain**
3. Copy the URL (e.g., `https://pub-abc123.r2.dev`)
4. Your `VIBECAST_R2_PUBLIC_URL` will be: `https://pub-abc123.r2.dev`

### Generate API Token

1. Go to **R2 Object Storage** main page
2. Click **Manage R2 API Tokens**
3. Click **Create API token**
4. Name: `vibecast-pipeline`
5. Permissions: **Object Read & Write**
6. Bucket: Select your `vibecast` bucket
7. Click **Create API Token**
8. **Copy both values** (secret shown only once):
   - Access Key ID → `R2_ACCESS_KEY_ID`
   - Secret Access Key → `R2_SECRET_ACCESS_KEY`

### Find Account ID

Your Account ID is in the URL: `https://dash.cloudflare.com/[ACCOUNT_ID]/...`

## 3. GitHub Repository Setup

### Add Secrets

Go to **Settings → Secrets and variables → Actions** and add:

**Required (4):**

| Secret | Value |
|--------|-------|
| `OPENAI_API_KEY` | `sk-...` |
| `R2_ACCOUNT_ID` | Your Cloudflare Account ID |
| `R2_ACCESS_KEY_ID` | R2 API Access Key |
| `R2_SECRET_ACCESS_KEY` | R2 API Secret Key |

**Personal Settings (10):**

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

### Enable GitHub Pages

1. Go to **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`, folder: `/site`
4. Click **Save**

Your site: `https://[username].github.io/vibecast/`

## 4. Configure Your Podcast

### Find Your Coordinates

Go to [latlong.net](https://www.latlong.net/) and search for your city.

### Schedule

Edit `.github/workflows/daily.yml` to change the time:

```yaml
schedule:
  - cron: "15 12 * * *"  # 12:15 UTC = 7:15 AM ET (winter)
```

Use [crontab.guru](https://crontab.guru/) to convert times.

## 5. Test

### Manual Trigger

1. Go to **Actions** tab
2. Click **Daily Podcast**
3. Click **Run workflow**
4. Set `dry_run: true` for testing

### Local Testing

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values

# Test
set -a && source .env && set +a
python -m podcast.run_daily --dry-run -v
```

## 6. Subscribe

Once your first episode is generated:

1. Copy your feed URL: `https://[username].github.io/vibecast/feed.xml`
2. Add to your podcast app:
   - **Overcast**: Add URL
   - **Apple Podcasts**: Library → Add Show by URL
   - **Pocket Casts**: Search → Add by URL

## Troubleshooting

### "R2 connection check failed"

- Verify R2 credentials in GitHub Secrets
- Check bucket name matches config
- Ensure API token has read/write permissions

### "No content items available"

- RSS feeds may be empty or blocked
- Check block_keywords aren't too aggressive
- Add more RSS sources

### "OpenAI API error"

- Verify API key is valid with billing enabled
- Check usage limits
- Ensure model names are correct

### Feed not updating

- Check GitHub Actions logs
- Ensure workflow has `contents: write` permission
- Verify GitHub Pages is enabled

## Cost Summary

**Per episode:**
- GPT-4o-mini: ~$0.01-0.02
- TTS: ~$0.03-0.10
- **Total: ~$0.05-0.15**

**Monthly (30 episodes):** ~$1.50-4.50

**Free services:**
- GitHub Actions: 2000 min/month
- GitHub Pages: Unlimited
- Cloudflare R2: 10GB storage, 10M requests
