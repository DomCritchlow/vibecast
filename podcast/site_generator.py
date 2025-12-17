"""Generate the landing page from config."""

import os
from pathlib import Path
from urllib.parse import urlparse


def generate_index_html(config: dict) -> str:
    """Generate the index.html landing page from config.
    
    Args:
        config: Full configuration dictionary.
    
    Returns:
        HTML string for index.html.
    """
    podcast = config.get("podcast", {})
    vibe = config.get("vibe", {})
    episode_config = config.get("episode", {})
    storage = config.get("storage", {})
    r2_config = storage.get("r2", {})
    sources_config = config.get("sources", {})
    openai_config = config.get("openai", {})
    
    # Extract values with defaults
    title = podcast.get("title", "Vibecast")
    short_title = title.split(":")[0].strip() if ":" in title else title
    tagline = podcast.get("tagline", "A daily podcast of good news and good vibes.")
    author = podcast.get("author", "")
    author_url = podcast.get("author_url", "")
    artwork_url = podcast.get("artwork_url", "")
    
    # Vibe-specific
    mood = vibe.get("mood", {})
    mood_primary = mood.get("primary", "uplifting")
    mood_secondary = mood.get("secondary", "optimistic")
    voice_persona = vibe.get("voice_persona", {})
    persona_name = voice_persona.get("name", "Your daily companion")
    personality_traits = voice_persona.get("personality", [])
    embrace = vibe.get("embrace", {})
    embrace_topics = embrace.get("topics", [])
    
    # Episode details
    target_minutes = episode_config.get("target_minutes", 4)
    
    # TTS voice
    tts_config = openai_config.get("tts", {})
    tts_voice = tts_config.get("voice", "nova")
    
    # Get enabled RSS sources with their URLs
    rss_sources = sources_config.get("rss", [])
    enabled_sources = [s for s in rss_sources if s.get("enabled", True)]
    
    # Extract source info (name and base URL)
    def get_base_url(feed_url: str) -> str:
        """Extract the base website URL from an RSS feed URL."""
        try:
            parsed = urlparse(feed_url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return feed_url
    
    source_info = [
        {"name": s.get("name", "Unknown"), "url": get_base_url(s.get("url", ""))}
        for s in enabled_sources
    ]
    
    # R2 public URL for transcripts (from env or config)
    r2_public_url = os.environ.get("VIBECAST_R2_PUBLIC_URL", r2_config.get("public_base_url", ""))
    
    # Build author link
    if author_url:
        author_html = f'<a href="{author_url}">{author}</a>'
    elif author:
        author_html = author
    else:
        author_html = "Vibecast"
    
    # Build dynamic description from vibe config
    first_trait = personality_traits[0] if personality_traits else "brings you the best news"
    dynamic_description = f"{persona_name} — {first_trait}. Every day, it gathers weather and uplifting stories, then delivers a short audio briefing to start your day right."
    
    # Build source pills HTML (all sources, clickable)
    source_pills = ""
    for source in source_info:
        source_pills += f'<a href="{source["url"]}" class="pill" target="_blank" rel="noopener">{source["name"]}</a>'
    
    # Build embrace topics for features (pick first 3)
    topics_text = ", ".join(embrace_topics[:3]) if embrace_topics else "positive stories"
    
    # Voice descriptions
    voice_descriptions = {
        "alloy": "balanced & versatile",
        "echo": "warm & conversational",
        "fable": "expressive & dynamic",
        "onyx": "deep & authoritative",
        "nova": "friendly & warm",
        "shimmer": "soft & gentle",
    }
    voice_desc = voice_descriptions.get(tts_voice, "natural")
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{short_title}</title>
    <meta name="description" content="{tagline}">
    <link rel="alternate" type="application/rss+xml" title="{title} RSS Feed" href="feed.xml">
    <style>
        :root {{
            --color-text: #1a1a1a;
            --color-text-muted: #666;
            --color-bg: #fff;
            --color-border: #eee;
            --color-accent: #f7b955;
            --color-accent-hover: #e5a63d;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            line-height: 1.6;
            min-height: 100vh;
        }}

        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 80px 24px;
        }}

        header {{
            margin-bottom: 48px;
            display: flex;
            gap: 24px;
            align-items: flex-start;
        }}

        .header-artwork {{
            width: 120px;
            height: 120px;
            border-radius: 16px;
            flex-shrink: 0;
            background: linear-gradient(135deg, #f7b955 0%, #ff8a5b 50%, #ea5455 100%);
            box-shadow: 0 8px 24px rgba(247, 185, 85, 0.3);
        }}

        .header-artwork img {{
            width: 100%;
            height: 100%;
            border-radius: 16px;
            object-fit: cover;
        }}

        .header-text {{
            flex: 1;
            min-width: 0;
        }}

        h1 {{
            font-size: 1.5rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            margin-bottom: 8px;
        }}

        .tagline {{
            font-size: 1.1rem;
            color: var(--color-text-muted);
            margin-bottom: 12px;
        }}

        main {{
            margin-bottom: 48px;
        }}

        .description {{
            font-size: 1rem;
            color: var(--color-text);
            margin-bottom: 32px;
            line-height: 1.7;
        }}

        .features {{
            margin-bottom: 32px;
            padding-left: 0;
            list-style: none;
        }}

        .features li {{
            position: relative;
            padding-left: 24px;
            margin-bottom: 8px;
            color: var(--color-text-muted);
        }}

        .features li::before {{
            content: "☀";
            position: absolute;
            left: 0;
            color: var(--color-accent);
        }}

        /* Source pills */
        .sources {{
            margin-bottom: 24px;
        }}

        .sources-label {{
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--color-text-muted);
            margin-bottom: 10px;
        }}

        .pills {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .pill {{
            font-size: 0.75rem;
            padding: 4px 10px;
            background: #f5f5f5;
            border-radius: 20px;
            color: var(--color-text-muted);
            text-decoration: none;
            transition: background 0.15s, color 0.15s;
        }}

        a.pill:hover {{
            background: var(--color-accent);
            color: white;
        }}

        .pill-muted {{
            background: transparent;
            border: 1px dashed #ddd;
        }}

        /* Vibe badge */
        .vibe-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 0.8rem;
            color: var(--color-text-muted);
            margin-top: 12px;
        }}

        .vibe-badge .mood {{
            display: inline-flex;
            gap: 4px;
        }}

        .vibe-badge .mood span {{
            padding: 2px 8px;
            background: linear-gradient(135deg, #f7b955 0%, #ff8a5b 100%);
            color: white;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 500;
        }}

        .rss-section {{
            margin-bottom: 32px;
        }}

        .rss-label {{
            font-size: 0.8rem;
            color: var(--color-text-muted);
            margin-bottom: 8px;
        }}

        .rss-url {{
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 0.85rem;
            color: var(--color-text-muted);
            background: #f5f5f5;
            padding: 12px 16px;
            border-radius: 8px;
            word-break: break-all;
            cursor: pointer;
            transition: background 0.15s;
        }}

        .rss-url:hover {{
            background: #eee;
        }}

        .episodes {{
            border-top: 1px solid var(--color-border);
            padding-top: 32px;
        }}

        .episodes h2 {{
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--color-text-muted);
            margin-bottom: 16px;
        }}

        /* Featured (latest) episode */
        .episode-featured {{
            background: #fafafa;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 24px;
        }}

        .episode-featured .episode-row {{
            flex-direction: column;
            gap: 16px;
        }}

        .episode-featured .episode-art {{
            width: 100%;
            height: 200px;
            border-radius: 12px;
        }}

        .episode-featured .episode-info h3 {{
            font-size: 1.1rem;
            white-space: normal;
        }}

        .episode-featured .episode-description {{
            margin-top: 12px;
            font-size: 0.9rem;
            color: var(--color-text-muted);
            line-height: 1.6;
        }}

        /* Regular episodes */
        .episode {{
            padding: 16px 0;
            border-bottom: 1px solid var(--color-border);
        }}

        .episode:last-child {{
            border-bottom: none;
        }}

        .episode-row {{
            display: flex;
            align-items: flex-start;
            gap: 16px;
        }}

        .episode-art {{
            width: 64px;
            height: 64px;
            background: linear-gradient(135deg, #f7b955 0%, #ff8a5b 50%, #ea5455 100%);
            border-radius: 8px;
            flex-shrink: 0;
        }}

        .episode-info {{
            flex: 1;
            min-width: 0;
        }}

        .episode-info h3 {{
            font-size: 0.95rem;
            font-weight: 500;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .episode-meta {{
            font-size: 0.8rem;
            color: var(--color-text-muted);
            margin-bottom: 6px;
        }}

        .episode-description {{
            font-size: 0.85rem;
            color: var(--color-text-muted);
            line-height: 1.5;
            margin-top: 8px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        .episode-links {{
            display: flex;
            gap: 12px;
            font-size: 0.8rem;
            margin-top: 8px;
        }}

        .episode-links button {{
            background: none;
            border: none;
            color: var(--color-accent);
            cursor: pointer;
            font-size: 0.8rem;
            font-family: inherit;
            padding: 0;
        }}

        .episode-links button:hover {{
            text-decoration: underline;
        }}

        /* Audio Player */
        .audio-player {{
            margin-top: 12px;
            padding: 12px;
            background: #f8f8f8;
            border-radius: 8px;
            display: none;
        }}

        .audio-player.active {{
            display: block;
            animation: slideDown 0.2s ease-out;
        }}

        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .audio-player audio {{
            width: 100%;
            height: 40px;
        }}

        /* Transcript Modal */
        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.2s, visibility 0.2s;
            padding: 20px;
        }}

        .modal-overlay.active {{
            opacity: 1;
            visibility: visible;
        }}

        .modal {{
            background: white;
            border-radius: 16px;
            max-width: 600px;
            width: 100%;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            transform: translateY(20px);
            transition: transform 0.2s;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        }}

        .modal-overlay.active .modal {{
            transform: translateY(0);
        }}

        .modal-header {{
            padding: 20px 24px;
            border-bottom: 1px solid var(--color-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .modal-header h3 {{
            font-size: 1.1rem;
            font-weight: 600;
        }}

        .modal-close {{
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--color-text-muted);
            padding: 4px 8px;
            line-height: 1;
            border-radius: 4px;
        }}

        .modal-close:hover {{
            background: #f5f5f5;
        }}

        .modal-body {{
            padding: 24px;
            overflow-y: auto;
            flex: 1;
        }}

        .transcript-text {{
            white-space: pre-wrap;
            font-size: 0.95rem;
            line-height: 1.8;
            color: var(--color-text);
        }}

        .transcript-loading {{
            text-align: center;
            color: var(--color-text-muted);
            padding: 40px;
        }}

        .transcript-error {{
            text-align: center;
            color: #e74c3c;
            padding: 40px;
        }}

        footer {{
            padding-top: 32px;
            border-top: 1px solid var(--color-border);
            font-size: 0.85rem;
            color: var(--color-text-muted);
        }}

        footer a {{
            color: var(--color-text);
            text-decoration: none;
        }}

        footer a:hover {{
            text-decoration: underline;
        }}

        @media (max-width: 500px) {{
            .container {{
                padding: 48px 20px;
            }}

            header {{
                flex-direction: column;
                align-items: center;
                text-align: center;
            }}

            .header-artwork {{
                width: 100px;
                height: 100px;
            }}

            .episode-featured .episode-art {{
                height: 160px;
            }}

            .modal {{
                max-height: 90vh;
            }}

            .modal-body {{
                padding: 16px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-artwork">
                <img src="{artwork_url}" alt="{short_title}" onerror="this.style.display='none'">
            </div>
            <div class="header-text">
                <h1>{short_title}</h1>
                <p class="tagline">{tagline}</p>
                <div class="vibe-badge">
                    <span class="mood"><span>{mood_primary}</span><span>{mood_secondary}</span></span>
                    <span>· {tts_voice} voice ({voice_desc})</span>
                </div>
            </div>
        </header>

        <main>
            <p class="description">{dynamic_description}</p>

            <ul class="features">
                <li>~{target_minutes} minutes of {mood_primary} content</li>
                <li>Local weather for your area</li>
                <li>Focus on {topics_text}</li>
                <li>New episode every day</li>
            </ul>

            <div class="sources">
                <p class="sources-label">Curated from</p>
                <div class="pills">{source_pills}</div>
            </div>

            <div class="rss-section">
                <p class="rss-label">Copy the feed URL to subscribe in your podcast app:</p>
                <div class="rss-url" id="rss-url" onclick="copyToClipboard(this)"></div>
            </div>

            <div class="episodes" id="episodes-list"></div>
        </main>

        <footer>
            <p>Made by {author_html} · Powered by good vibes ☀️</p>
        </footer>
    </div>

    <!-- Transcript Modal -->
    <div class="modal-overlay" id="transcript-modal">
        <div class="modal">
            <div class="modal-header">
                <h3 id="modal-title">Transcript</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div id="modal-content" class="transcript-text"></div>
            </div>
        </div>
    </div>

    <script>
        const feedUrl = new URL('feed.xml', window.location.href).href;
        const r2BaseUrl = '{r2_public_url}'.replace(/\\/+$/, '');
        const transcriptBaseUrl = r2BaseUrl + '/transcripts/';
        document.getElementById('rss-url').textContent = feedUrl;

        let currentAudio = null;
        let currentPlayerId = null;

        function copyToClipboard(el) {{
            navigator.clipboard.writeText(el.textContent);
            const original = el.textContent;
            el.textContent = 'Copied!';
            setTimeout(() => el.textContent = original, 1500);
        }}

        function togglePlayer(episodeId, audioUrl) {{
            const player = document.getElementById('player-' + episodeId);
            const audio = document.getElementById('audio-' + episodeId);
            const btn = document.getElementById('btn-' + episodeId);
            
            // If clicking on currently playing episode, toggle it
            if (currentPlayerId === episodeId) {{
                if (audio.paused) {{
                    audio.play();
                    btn.textContent = '⏸ Pause';
                }} else {{
                    audio.pause();
                    btn.textContent = '▶ Listen';
                }}
                return;
            }}
            
            // Stop any currently playing audio
            if (currentAudio && !currentAudio.paused) {{
                currentAudio.pause();
                const prevBtn = document.getElementById('btn-' + currentPlayerId);
                if (prevBtn) prevBtn.textContent = '▶ Listen';
                const prevPlayer = document.getElementById('player-' + currentPlayerId);
                if (prevPlayer) prevPlayer.classList.remove('active');
            }}
            
            // Show and play the new player
            player.classList.add('active');
            audio.play();
            btn.textContent = '⏸ Pause';
            currentAudio = audio;
            currentPlayerId = episodeId;
        }}

        function onAudioEnded(episodeId) {{
            const btn = document.getElementById('btn-' + episodeId);
            if (btn) btn.textContent = '▶ Listen';
        }}

        function openTranscript(title, transcriptUrl) {{
            const modal = document.getElementById('transcript-modal');
            const modalTitle = document.getElementById('modal-title');
            const modalContent = document.getElementById('modal-content');
            
            modalTitle.textContent = title;
            modalContent.innerHTML = '<div class="transcript-loading">Loading transcript...</div>';
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
            
            fetch(transcriptUrl)
                .then(r => {{
                    if (!r.ok) throw new Error('Failed to load');
                    return r.text();
                }})
                .then(text => {{
                    modalContent.textContent = text;
                }})
                .catch(err => {{
                    modalContent.innerHTML = '<div class="transcript-error">Could not load transcript</div>';
                }});
        }}

        function closeModal() {{
            const modal = document.getElementById('transcript-modal');
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }}

        // Close modal on overlay click
        document.getElementById('transcript-modal').addEventListener('click', (e) => {{
            if (e.target.classList.contains('modal-overlay')) {{
                closeModal();
            }}
        }});

        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});

        fetch('feed.xml')
            .then(r => r.text())
            .then(xml => {{
                const parser = new DOMParser();
                const doc = parser.parseFromString(xml, 'text/xml');
                const items = doc.querySelectorAll('item');
                const maxEpisodes = 7;
                
                if (items.length === 0) return;
                
                let episodesHtml = '';
                
                for (let i = 0; i < Math.min(items.length, maxEpisodes); i++) {{
                    const item = items[i];
                    const title = item.querySelector('title')?.textContent || 'Episode';
                    const pubDate = item.querySelector('pubDate')?.textContent;
                    const guid = item.querySelector('guid')?.textContent || '';
                    const description = item.querySelector('description')?.textContent || '';
                    const enclosure = item.querySelector('enclosure');
                    const audioUrl = enclosure?.getAttribute('url') || '';
                    
                    const allChildren = item.children;
                    let duration = '~4 min';
                    let imageUrl = '';
                    let summary = '';
                    for (let j = 0; j < allChildren.length; j++) {{
                        const child = allChildren[j];
                        const localName = child.localName || child.nodeName.split(':').pop();
                        if (localName === 'duration') {{
                            duration = child.textContent;
                        }}
                        if (localName === 'image' && child.hasAttribute('href')) {{
                            imageUrl = child.getAttribute('href');
                        }}
                        if (localName === 'summary') {{
                            summary = child.textContent;
                        }}
                    }}
                    
                    // Fallback: try getElementsByTagName for itunes:image
                    if (!imageUrl) {{
                        const itunesImages = item.getElementsByTagName('itunes:image');
                        if (itunesImages.length > 0) {{
                            imageUrl = itunesImages[0].getAttribute('href');
                        }}
                    }}
                    
                    // Use summary or description, clean HTML tags
                    const episodeDesc = (summary || description).replace(/<[^>]*>/g, '').trim();
                    
                    let dateStr = '';
                    if (pubDate) {{
                        const d = new Date(pubDate);
                        dateStr = d.toLocaleDateString('en-US', {{ weekday: 'short', month: 'short', day: 'numeric' }});
                    }}
                    
                    const artStyle = imageUrl 
                        ? `background-image: url('${{imageUrl}}'); background-size: cover; background-position: center;`
                        : `background: linear-gradient(135deg, #f7b955 0%, #ff8a5b 50%, #ea5455 100%);`;
                    
                    const transcriptUrl = transcriptBaseUrl + guid + '.txt';
                    const episodeId = guid || i;
                    const escapedTitle = title.replace(/'/g, "\\\\'");
                    const escapedUrl = transcriptUrl.replace(/'/g, "\\\\'");
                    
                    const isFeatured = i === 0;
                    const episodeClass = isFeatured ? 'episode episode-featured' : 'episode';
                    const sectionHeader = isFeatured ? '<h2>Latest Episode</h2>' : (i === 1 ? '<h2>Previous Episodes</h2>' : '');
                    
                    episodesHtml += sectionHeader + `
                        <div class="${{episodeClass}}">
                            <div class="episode-row">
                                <div class="episode-art" style="${{artStyle}}"></div>
                                <div class="episode-info">
                                    <h3>${{title}}</h3>
                                    <p class="episode-meta">${{dateStr}} · ${{duration}}</p>
                                    ${{episodeDesc ? `<p class="episode-description">${{episodeDesc}}</p>` : ''}}
                                    <div class="episode-links">
                                        <button id="btn-${{episodeId}}" onclick="togglePlayer('${{episodeId}}', '${{audioUrl}}')">▶ Listen</button>
                                        <button onclick="openTranscript('${{escapedTitle}}', '${{escapedUrl}}')">📄 Transcript</button>
                                    </div>
                                </div>
                            </div>
                            <div class="audio-player" id="player-${{episodeId}}">
                                <audio id="audio-${{episodeId}}" src="${{audioUrl}}" preload="none" onended="onAudioEnded('${{episodeId}}')" controls></audio>
                            </div>
                        </div>
                    `;
                }}
                
                document.getElementById('episodes-list').innerHTML = episodesHtml;
            }})
            .catch(err => {{ console.error('Feed error:', err); }});
    </script>
</body>
</html>'''
    
    return html


def save_index_html(config: dict, site_dir: Path) -> None:
    """Generate and save index.html to the site directory.
    
    Args:
        config: Full configuration dictionary.
        site_dir: Path to the site directory.
    """
    html = generate_index_html(config)
    
    index_path = site_dir / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

