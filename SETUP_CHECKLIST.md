# Setup Checklist

Use this checklist when setting up your fork of Vibecast.

## ✅ Pre-Deployment Checklist

### 1. Customize Configuration

- [ ] **Open `podcast/config.yaml`**
- [ ] **Line ~65:** Change `author: "Your Name"` to your actual name
- [ ] **Line ~73:** Change `github_url:` to `https://github.com/YOUR_USERNAME/vibecast`
- [ ] **Line ~107-109:** Set your location (name, lat, lon) or use env variables
- [ ] **Customize the vibe** (mood, personality, voice) to match your preference
- [ ] **Review RSS sources** — add/remove sources based on your interests

**Privacy Alternative:** Instead of editing config.yaml, you can set environment variables:
- `VIBECAST_AUTHOR="Your Name"`
- `VIBECAST_LOCATION_NAME="Your City"`
- `VIBECAST_LOCATION_LAT=40.7128`
- `VIBECAST_LOCATION_LON=-74.0060`

### 2. Set Up Cloudflare R2

- [ ] Create a Cloudflare account (if needed)
- [ ] Go to R2 → Create bucket (name it `vibecast` or similar)
- [ ] Enable public access on the bucket
- [ ] Copy the R2.dev subdomain URL (e.g., `pub-xxxxx.r2.dev`)
- [ ] Create API token with Object Read & Write permissions
- [ ] Save Account ID, Access Key ID, and Secret Access Key

### 3. Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

**Required:**
- [ ] `OPENAI_API_KEY` — Your OpenAI API key
- [ ] `R2_ACCOUNT_ID` — From Cloudflare dashboard
- [ ] `R2_ACCESS_KEY_ID` — From R2 API token
- [ ] `R2_SECRET_ACCESS_KEY` — From R2 API token

**Recommended:**
- [ ] `VIBECAST_AUTHOR` — Your name
- [ ] `VIBECAST_OWNER_EMAIL` — Your email
- [ ] `VIBECAST_LOCATION_NAME` — Your city
- [ ] `VIBECAST_LOCATION_LAT` — Your latitude
- [ ] `VIBECAST_LOCATION_LON` — Your longitude  
- [ ] `VIBECAST_R2_PUBLIC_URL` — Your R2.dev URL (e.g., `https://pub-xxxxx.r2.dev`)

**Optional:**
- [ ] `ELEVENLABS_API_KEY` — Only if using ElevenLabs TTS

### 4. Enable GitHub Pages

- [ ] Go to **Settings → Pages**
- [ ] **Source:** Deploy from a branch
- [ ] **Branch:** `main`
- [ ] **Folder:** `/docs`
- [ ] Click **Save**
- [ ] Wait for GitHub to provide your URL (e.g., `yourusername.github.io/vibecast`)

### 5. Update Deployment URLs (After GitHub Pages is enabled)

Either update config.yaml OR add these as GitHub Secrets:

- [ ] `VIBECAST_SITE_URL` — Your GitHub Pages URL
- [ ] `VIBECAST_FEED_URL` — Your GitHub Pages URL + `/feed.xml`
- [ ] `VIBECAST_ARTWORK_URL` — Your GitHub Pages URL + `/artwork.png`

Example:
```
VIBECAST_SITE_URL=https://yourusername.github.io/vibecast/
VIBECAST_FEED_URL=https://yourusername.github.io/vibecast/feed.xml
VIBECAST_ARTWORK_URL=https://yourusername.github.io/vibecast/artwork.png
```

### 6. Test Your Setup

**Option A: Run check script locally**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python check_config.py
```

**Option B: Run in GitHub Actions**
- [ ] Go to **Actions** tab
- [ ] Click **Daily Podcast** workflow
- [ ] Click **Run workflow**
- [ ] Select **dry_run: true**
- [ ] Click **Run workflow**
- [ ] Check the logs to ensure no errors

### 7. First Real Run

- [ ] Go to **Actions** → **Daily Podcast**
- [ ] Click **Run workflow** (leave dry_run as false)
- [ ] Wait ~2 minutes for completion
- [ ] Visit your GitHub Pages URL to see your podcast!

### 8. Subscribe to Your Podcast

- [ ] Open your podcast website
- [ ] Click the RSS button to copy your feed URL
- [ ] Add the feed to your podcast app (Apple Podcasts, Overcast, etc.)

## 🎉 You're Done!

Your podcast will now generate automatically every day at 4:00 AM UTC.

### Optional: Customize Schedule

Edit `.github/workflows/daily.yml` line 7 to change the schedule:

```yaml
- cron: "0 4 * * *"  # 4:00 AM UTC
```

Use [crontab.guru](https://crontab.guru/) to help with cron syntax.

### Optional: Customize Homepage

The homepage is auto-generated from your config. To customize further:
- The generator is in `podcast/site_generator.py`
- Artwork is in `docs/artwork.svg` and `docs/artwork.png`
- Styles are inline in the generated HTML

## Need Help?

- Check [QUICKSTART.md](QUICKSTART.md) for detailed instructions
- Read [CONTRIBUTING.md](CONTRIBUTING.md) if you want to modify code
- Open an issue if something's broken
- Start a discussion for questions or to share your podcast!

