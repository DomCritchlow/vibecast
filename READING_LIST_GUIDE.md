# Reading List Feature Guide

The reading list feature allows you to curate long-form articles (like Substack newsletters) that get a compelling mention in your podcast, but aren't fully summarized. This is perfect for content you want to actually **read** rather than just hear about.

## How It Works

1. **Fetch**: Reading list sources are fetched from RSS feeds (just like news sources)
2. **Mention**: Instead of being summarized in the main briefing, they get a dedicated 30-45 second segment
3. **Describe**: The AI host describes what each article is about in 1-2 compelling sentences
4. **Link**: Full links appear in the show notes and transcript

## Example Output

The podcast might sound like:

> "A couple things for your reading list this week. On Platformer, Casey Newton digs into the TikTok ban - the legal mechanics, what it means for creators, and why the courts might actually side with ByteDance this time. And Zvi has his weekly AI roundup covering OpenAI's o3 release, some skepticism on AI safety theater, and his take on why regulation is moving faster than expected. Links in the show notes."

## Adding Your Substack Subscriptions

### Step 1: Find the RSS Feed URL

Every Substack has a built-in RSS feed:

```
https://{publication-name}.substack.com/feed
```

Examples:
- `https://platformer.news/feed`
- `https://aisnakeoil.substack.com/feed`
- `https://thezvi.substack.com/feed`

### Step 2: Add to Config

Edit `podcast/config.yaml` and add sources under `sources.reading_list.sources`:

```yaml
reading_list:
  max_items: 3  # Maximum articles to recommend per episode
  
  sources:
    - name: "Platformer"
      url: "https://platformer.news/feed"
      author: "Casey Newton"
      enabled: true
      description: "Tech policy and platform accountability"
      tags: ["tech", "policy"]
    
    - name: "Your Favorite Substack"
      url: "https://yoursubstack.substack.com/feed"
      author: "Author Name"
      enabled: true
      description: "What this publication is about"
      tags: ["topic1", "topic2"]
```

### Step 3: Test It

Run a dry run to see what would be fetched:

```bash
python -m podcast.run_daily --dry-run -v
```

## Configuration Options

### Per-Source Options

- **name**: Display name for the publication
- **url**: RSS feed URL (format: `https://{name}.substack.com/feed`)
- **author**: Writer's name (appears in show notes)
- **enabled**: Set to `false` to temporarily disable
- **description**: Brief description of what the publication covers (helps the AI write better descriptions)
- **tags**: Category tags for organization

### Global Options

- **max_items**: Maximum reading list articles per episode (default: 3)

## How Reading List Differs from Briefing Sources

| Feature | Briefing Sources | Reading List |
|---------|-----------------|--------------|
| **Treatment** | Fully summarized in the episode | Briefly described, meant to be read |
| **Duration** | 4-6 sentences per story (~80-100 words) | 1-2 sentences total (~60-80 words for all) |
| **Purpose** | Stay informed | Discover deeper content |
| **Best For** | News, updates, quick facts | Long-form analysis, essays, deep dives |

## Tips for Curating Your Reading List

1. **Quality over quantity**: Set `max_items: 3` or less - this segment should be brief
2. **Diverse voices**: Include writers with different perspectives
3. **Publication frequency matters**: Weekly roundups work great; daily posts might overwhelm
4. **Good descriptions help**: The `description` field helps the AI write better recommendations

## Discovering New Substacks

Looking for recommendations? Check out:
- **Tech/AI**: Platformer, AI Snake Oil, Zvi on AI, Ben Thompson (Stratechery)
- **Culture**: Garbage Day, Embedded
- **Science**: Your Local Epidemiologist, Slow Boring
- **Writing/Media**: The Honest Broker, Heated

## Finding Your Subscriptions

If you already subscribe to Substacks:

1. Go to `https://substack.com/settings/subscriptions`
2. For each publication, the URL is usually `https://{name}.substack.com`
3. Add `/feed` to get the RSS URL

## Troubleshooting

### "Fetched 0 reading list items"

**Check:**
- Is `enabled: true` for at least one source?
- Is the RSS URL correct? (Should end with `/feed`)
- Does the Substack have recent posts?

### "Reading list segment too long"

**Fix:**
- Reduce `max_items` to 2 or 1
- The AI should keep descriptions brief, but you can adjust the episode structure

### "Some Substacks aren't showing up"

**Cause:**
- Reading list items are sorted by date (most recent first)
- Only `max_items` are selected

**Fix:**
- Increase `max_items`
- Or disable less important sources

## Example: Complete Reading List Config

```yaml
sources:
  reading_list:
    max_items: 3
    
    sources:
      # Tech & AI
      - name: "Platformer"
        url: "https://platformer.news/feed"
        author: "Casey Newton"
        enabled: true
        description: "Tech policy and platform accountability"
        tags: ["tech", "policy"]
      
      - name: "AI Snake Oil"
        url: "https://aisnakeoil.substack.com/feed"
        author: "Arvind Narayanan & Sayash Kapoor"
        enabled: true
        description: "Critical analysis of AI hype and claims"
        tags: ["ai", "criticism"]
      
      - name: "Zvi on AI"
        url: "https://thezvi.substack.com/feed"
        author: "Zvi Mowshowitz"
        enabled: true
        description: "Weekly AI policy and development roundups"
        tags: ["ai", "policy"]
      
      # Add more as needed...
```

## Advanced: Email-Based Discovery

Want to auto-discover Substacks from your email subscriptions? See `CONTENT_SOURCES_RESEARCH.md` for ideas on building an email parser that extracts Substack URLs from your inbox.
