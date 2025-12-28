# Example Vibecast Configurations

This directory contains example configurations showcasing different podcast vibes and use cases.

## How to Use These Examples

1. Copy an example config to `podcast/config.yaml`
2. Customize the personal settings (location, author, etc.)
3. Run your podcast!

```bash
# Example: Use the calm morning config
cp examples/calm-morning.yaml podcast/config.yaml
# Edit podcast/config.yaml with your personal details
python -m podcast.run_daily --dry-run -v
```

## Available Examples

### `calm-morning.yaml`
**Perfect for:** Meditation, gentle wake-ups, quiet mornings
- 🧘 **Vibe:** Calm, gentle, mindful
- 🗣️ **Voice:** Shimmer (soft, gentle)
- 📰 **Focus:** Wellness, nature, positive science
- ⏱️ **Duration:** 5 minutes

### `energetic-commute.yaml`
**Perfect for:** Workouts, morning commutes, getting pumped
- ⚡ **Vibe:** Energetic, motivational, upbeat
- 🗣️ **Voice:** Nova (friendly, warm)
- 📰 **Focus:** Innovation, breakthroughs, inspiring stories
- ⏱️ **Duration:** 8 minutes

### `tech-focused.yaml`
**Perfect for:** Developers, tech enthusiasts, early adopters
- 💻 **Vibe:** Informed, curious, technical
- 🗣️ **Voice:** Echo (conversational male)
- 📰 **Focus:** Tech news, AI, open source, space
- ⏱️ **Duration:** 10 minutes

### `local-news-nyc.yaml`
**Perfect for:** City dwellers who want local + global
- 🏙️ **Vibe:** Connected, community-focused
- 🗣️ **Voice:** Fable (storyteller)
- 📰 **Focus:** NYC local news + positive global stories
- ⏱️ **Duration:** 6 minutes

## Create Your Own

Mix and match elements from these examples:

- **Mood combinations:** Try "calm" + "curious", "energetic" + "empathetic"
- **Voice experiments:** Test all 6 voices to find your favorite
- **Topic filtering:** Be specific about what you want/don't want
- **Source diversity:** Mix mainstream, indie, and specialized feeds

## Share Your Config!

Created an awesome vibe? Share it!
- Open a PR to add it to this directory
- Start a discussion to showcase your podcast
- Tag us on social media with your creation

## Tips

- Start with dry-run to test without API costs
- Tweak one thing at a time to see what works
- Listen to a few episodes before making big changes
- Your perfect vibe might take a few iterations—that's normal!

