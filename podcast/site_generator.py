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
    tts_root_config = config.get("tts", {})
    
    # Extract values with defaults
    title = podcast.get("title", "Vibecast")
    short_title = title.split(":")[0].strip() if ":" in title else title
    tagline = podcast.get("tagline", "A daily podcast of good news and good vibes.")
    author = podcast.get("author", "")
    author_url = podcast.get("author_url", "")
    artwork_url = podcast.get("artwork_url", "")
    github_url = podcast.get("github_url") or config.get("github_url", "https://github.com/domcritchlow/vibecast")
    
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
    
    # TTS voice - check provider and get from the right place
    tts_provider = tts_root_config.get("provider", "openai")
    if tts_provider == "openai":
        openai_tts = tts_root_config.get("openai", {})
        tts_voice = openai_tts.get("voice", "nova")
    else:  # elevenlabs
        elevenlabs_tts = tts_root_config.get("elevenlabs", {})
        tts_voice = elevenlabs_tts.get("voice_id", "rachel")
    
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
    
    # Build embrace topics for features (pick first 3)
    topics_text = ", ".join(embrace_topics[:3]) if embrace_topics else "positive stories"
    
    # Build dynamic description based on vibe and content
    dynamic_description = f"A daily {mood_primary} podcast bringing you weather, {topics_text}, and stories worth your time."
    
    # Build source pills HTML (all sources, clickable)
    source_pills = ""
    for source in source_info:
        source_pills += f'<a href="{source["url"]}" class="pill" target="_blank" rel="noopener">{source["name"]}</a>'
    
    # Voice descriptions (OpenAI TTS voices)
    voice_descriptions = {
        "alloy": "balanced & versatile",
        "ash": "expressive & dynamic",
        "ballad": "smooth & expressive",
        "cedar": "clear & natural",
        "coral": "warm & friendly",
        "echo": "warm & conversational",
        "fable": "expressive storyteller",
        "marin": "clear & professional",
        "nova": "friendly & warm",
        "onyx": "deep & authoritative",
        "sage": "clear & balanced",
        "shimmer": "soft & gentle",
        "verse": "natural & engaging",
    }
    voice_desc = voice_descriptions.get(tts_voice, "AI-narrated")
    
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
            --color-text-light: #999;
            --color-bg: #fafafa;
            --color-bg-white: #fff;
            --color-border: #e5e5e5;
            --color-accent: #1a1a1a;
            --color-accent-hover: #333;
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
            max-width: 720px;
            margin: 0 auto;
            padding: 100px 32px 80px;
        }}

        /* Hero Section - Compact */
        header {{
            text-align: center;
            margin-bottom: 48px;
            padding-bottom: 32px;
            border-bottom: 1px solid var(--color-border);
        }}

        h1 {{
            font-family: 'Playfair Display', 'Georgia', serif;
            font-size: 3rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 12px;
            line-height: 1;
            text-transform: uppercase;
        }}

        .tagline {{
            font-size: 1.1rem;
            color: var(--color-text-muted);
            font-weight: 400;
            line-height: 1.5;
        }}

        .header-nav {{
            margin-top: 16px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            font-size: 0.875rem;
        }}

        .header-nav a {{
            color: var(--color-text-light);
            text-decoration: none;
            transition: color 0.2s;
        }}

        .header-nav a:hover {{
            color: var(--color-accent);
        }}

        .header-nav span {{
            color: var(--color-border);
        }}

        /* Main Content */
        main {{
            margin-bottom: 80px;
        }}

        /* Latest Episode Hero */
        .latest-episode-hero {{
            background: var(--color-bg-white);
            border: 1px solid var(--color-border);
            border-radius: 16px;
            padding: 40px;
            margin-bottom: 48px;
        }}

        .latest-label {{
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--color-text-light);
            margin-bottom: 24px;
        }}

        .latest-episode-content {{
            display: flex;
            gap: 32px;
            align-items: flex-start;
            margin-bottom: 28px;
        }}

        .latest-episode-hero .episode-art {{
            width: 180px;
            height: 180px;
            border-radius: 12px;
            background: linear-gradient(135deg, #e0e0e0 0%, #c0c0c0 100%);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
            flex-shrink: 0;
        }}

        .latest-episode-info {{
            flex: 1;
            min-width: 0;
        }}

        .latest-episode-hero h2 {{
            font-family: 'Playfair Display', 'Georgia', serif;
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 12px;
            line-height: 1.3;
        }}

        .latest-episode-hero .episode-meta {{
            font-size: 0.9rem;
            color: var(--color-text-light);
            margin-bottom: 16px;
        }}

        .latest-episode-hero .episode-description {{
            font-size: 1rem;
            color: var(--color-text-muted);
            line-height: 1.6;
            margin-bottom: 0;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        .primary-actions {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }}

        .btn-primary {{
            padding: 12px 28px;
            background: var(--color-accent);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            font-family: inherit;
        }}

        .btn-primary:hover {{
            background: var(--color-accent-hover);
        }}

        .btn-secondary {{
            padding: 12px 24px;
            background: transparent;
            color: var(--color-accent);
            border: 1px solid var(--color-border);
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }}

        .btn-secondary:hover {{
            background: var(--color-bg);
            border-color: var(--color-accent);
        }}

        /* About Section */
        .about-section {{
            background: var(--color-bg-white);
            border: 1px solid var(--color-border);
            border-radius: 12px;
            padding: 40px;
            margin-bottom: 48px;
        }}

        .about-section h3 {{
            font-family: 'Playfair Display', 'Georgia', serif;
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 24px;
        }}

        .about-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }}

        .about-item {{
            text-align: left;
        }}

        .about-item-label {{
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--color-text-light);
            margin-bottom: 8px;
        }}

        .about-item-value {{
            font-size: 1rem;
            color: var(--color-text);
        }}

        .sources-label {{
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--color-text-light);
            margin-bottom: 12px;
        }}

        .pills {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .pill {{
            font-size: 0.75rem;
            padding: 4px 12px;
            background: var(--color-bg);
            border: 1px solid var(--color-border);
            border-radius: 20px;
            color: var(--color-text-muted);
            text-decoration: none;
            transition: all 0.2s;
        }}

        a.pill:hover {{
            background: var(--color-accent);
            color: white;
            border-color: var(--color-accent);
        }}

        /* Subscribe Section */
        .subscribe-section {{
            background: var(--color-bg-white);
            border: 1px solid var(--color-border);
            border-radius: 12px;
            padding: 40px;
            margin-bottom: 64px;
            text-align: center;
        }}

        .subscribe-section h3 {{
            font-family: 'Playfair Display', 'Georgia', serif;
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 12px;
        }}

        .subscribe-section p {{
            font-size: 1rem;
            color: var(--color-text-muted);
            margin-bottom: 24px;
        }}

        .rss-url {{
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 0.85rem;
            color: var(--color-text);
            background: var(--color-bg);
            padding: 14px 20px;
            border-radius: 8px;
            word-break: break-all;
            cursor: pointer;
            transition: background 0.2s;
            border: 1px solid var(--color-border);
            display: inline-block;
            max-width: 100%;
        }}

        .rss-url:hover {{
            background: #f5f5f5;
        }}

        /* Episodes List */
        .episodes {{
            margin-bottom: 64px;
        }}

        .episodes h2 {{
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--color-text-light);
            margin-bottom: 24px;
        }}

        /* Regular episodes - compact list */
        .episode {{
            background: var(--color-bg-white);
            border: 1px solid var(--color-border);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 12px;
            transition: border-color 0.2s;
        }}

        .episode:hover {{
            border-color: var(--color-accent);
        }}

        .episode-row {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}

        .episode-art {{
            width: 64px;
            height: 64px;
            background: linear-gradient(135deg, #e0e0e0 0%, #c0c0c0 100%);
            border-radius: 6px;
            flex-shrink: 0;
        }}

        .episode-info {{
            flex: 1;
            min-width: 0;
        }}

        .episode-info h3 {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 4px;
            line-height: 1.3;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .episode-meta {{
            font-size: 0.85rem;
            color: var(--color-text-light);
        }}

        .episode-actions {{
            display: flex;
            gap: 12px;
            flex-shrink: 0;
        }}

        .episode-actions button {{
            background: none;
            border: none;
            color: var(--color-text-muted);
            cursor: pointer;
            font-size: 1.2rem;
            font-family: inherit;
            padding: 8px;
            transition: color 0.2s;
            line-height: 1;
        }}

        .episode-actions button:hover {{
            color: var(--color-accent);
        }}

        .play-button {{
            font-size: 1.5rem !important;
        }}

        /* Audio Player */
        .audio-player {{
            margin-top: 16px;
            padding: 16px;
            background: var(--color-bg);
            border: 1px solid var(--color-border);
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
            background: rgba(0, 0, 0, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.2s, visibility 0.2s;
            padding: 24px;
        }}

        .modal-overlay.active {{
            opacity: 1;
            visibility: visible;
        }}

        .modal {{
            background: var(--color-bg-white);
            border-radius: 12px;
            max-width: 680px;
            width: 100%;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            transform: translateY(20px);
            transition: transform 0.2s;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.3);
        }}

        .modal-overlay.active .modal {{
            transform: translateY(0);
        }}

        .modal-header {{
            padding: 24px 32px;
            border-bottom: 1px solid var(--color-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .modal-header h3 {{
            font-size: 1.25rem;
            font-weight: 600;
        }}

        .modal-close {{
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--color-text-muted);
            padding: 8px 12px;
            line-height: 1;
            border-radius: 6px;
            transition: background 0.2s;
        }}

        .modal-close:hover {{
            background: var(--color-bg);
        }}

        .modal-body {{
            padding: 32px;
            overflow-y: auto;
            flex: 1;
        }}

        .transcript-text {{
            white-space: pre-wrap;
            font-size: 1rem;
            line-height: 1.8;
            color: var(--color-text);
        }}

        .show-notes-content {{
            font-size: 0.95rem;
            line-height: 1.7;
            color: var(--color-text);
            font-family: var(--font-sans);
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        .show-notes-content a {{
            color: var(--color-accent);
            text-decoration: none;
            border-bottom: 1px solid var(--color-border);
            transition: border-color 0.2s;
            word-break: break-all;
        }}

        .show-notes-content a:hover {{
            border-bottom-color: var(--color-accent);
        }}

        .transcript-loading {{
            text-align: center;
            color: var(--color-text-muted);
            padding: 60px;
        }}

        .transcript-error {{
            text-align: center;
            color: #e74c3c;
            padding: 60px;
        }}

        footer {{
            padding-top: 64px;
            text-align: center;
            font-size: 0.9rem;
            color: var(--color-text-light);
        }}

        .footer-links {{
            margin-top: 16px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}

        .footer-links a {{
            color: var(--color-text);
            text-decoration: none;
            transition: color 0.2s;
        }}

        .footer-links a:hover {{
            color: var(--color-accent);
        }}

        .footer-links span {{
            color: var(--color-text-light);
        }}

        footer a {{
            color: var(--color-text);
            text-decoration: none;
            transition: color 0.2s;
        }}

        footer a:hover {{
            color: var(--color-accent);
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 60px 24px 60px;
            }}

            h1 {{
                font-size: 2.5rem;
            }}

            .tagline {{
                font-size: 1rem;
            }}

            .latest-episode-hero {{
                padding: 28px 20px;
            }}

            .latest-episode-content {{
                flex-direction: column;
                gap: 20px;
            }}

            .latest-episode-hero .episode-art {{
                width: 140px;
                height: 140px;
            }}

            .latest-episode-hero h2 {{
                font-size: 1.4rem;
            }}

            .primary-actions {{
                flex-direction: column;
            }}

            .btn-primary,
            .btn-secondary {{
                width: 100%;
            }}

            .subscribe-section,
            .about-section {{
                padding: 32px 24px;
            }}

            .about-grid {{
                grid-template-columns: 1fr;
                gap: 20px;
            }}

            .episode-row {{
                gap: 12px;
            }}

            .episode-art {{
                width: 56px;
                height: 56px;
            }}

            .episode-info h3 {{
                font-size: 0.9rem;
            }}

            .episode-meta {{
                font-size: 0.8rem;
            }}

            .episode-actions {{
                flex-direction: column;
                gap: 8px;
            }}

            .modal {{
                max-height: 90vh;
            }}

            .modal-header {{
                padding: 20px 24px;
            }}

            .modal-body {{
                padding: 24px;
            }}
        }}

        @media (max-width: 480px) {{
            h1 {{
                font-size: 2rem;
            }}

            .latest-episode-hero .episode-art {{
                width: 120px;
                height: 120px;
            }}

            .latest-episode-hero h2 {{
                font-size: 1.2rem;
            }}
        }}
    </style>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800;900&display=swap" rel="stylesheet">
</head>
<body>
    <div class="container">
        <header>
                <h1>{short_title}</h1>
                <p class="tagline">{tagline}</p>
                <nav class="header-nav">
                    <a href="about.html">About This Show</a>
                    <span>·</span>
                    <a href="docs.html">About Vibecast</a>
                </nav>
        </header>

        <main>
            <!-- Latest Episode Hero -->
            <div class="latest-episode-hero" id="latest-episode-placeholder">
                <p class="latest-label">Latest Episode</p>
                <p style="color: var(--color-text-muted); padding: 40px 0;">Loading...</p>
            </div>

            <!-- Subscribe -->
            <div class="subscribe-section">
                <h3>Subscribe</h3>
                <p>Get new episodes automatically in your favorite podcast app</p>
                <div class="rss-url" id="rss-url" onclick="copyToClipboard(this)"></div>
            </div>

            <!-- Recent Episodes -->
            <div class="episodes">
                <h2>Recent Episodes</h2>
                <div id="episodes-list"></div>
            </div>

            <!-- About -->
            <div class="about-section">
                <h3>About This Show</h3>
                <div class="about-grid">
                    <div class="about-item">
                        <div class="about-item-label">Format</div>
                        <div class="about-item-value">~{target_minutes} minutes daily</div>
                    </div>
                    <div class="about-item">
                        <div class="about-item-label">Content</div>
                        <div class="about-item-value">{topics_text.capitalize()}</div>
                    </div>
                    <div class="about-item">
                        <div class="about-item-label">Voice</div>
                        <div class="about-item-value">{tts_voice} ({voice_desc})</div>
                    </div>
                    <div class="about-item">
                        <div class="about-item-label">Vibe</div>
                        <div class="about-item-value">{mood_primary.capitalize()}</div>
                    </div>
                </div>
                <div class="sources-label">Sources</div>
                <div class="pills">{source_pills}</div>
            </div>
        </main>

        <footer>
            <p>Made by {author_html}</p>
            <nav class="footer-links">
                <a href="about.html">About This Show</a>
                <span>·</span>
                <a href="docs.html">About Vibecast</a>
            </nav>
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
        // ===== Configuration =====
        const feedUrl = new URL('feed.xml', window.location.href).href;
        const r2BaseUrl = '{r2_public_url}'.replace(/\\/+$/, '');
        const transcriptBaseUrl = r2BaseUrl + '/transcripts/';
        document.getElementById('rss-url').textContent = feedUrl;

        // ===== State Management =====
        let currentAudio = null;
        let currentPlayerId = null;
        const episodeDescriptions = {{}};

        // ===== Utility Functions =====

        function copyToClipboard(el) {{
            navigator.clipboard.writeText(el.textContent);
            const original = el.textContent;
            el.textContent = 'Copied!';
            setTimeout(() => el.textContent = original, 1500);
        }}

        // Escape HTML to prevent XSS
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}

        // Convert URLs in text to clickable links
        function linkify(text) {{
            return text.split(' ').map(word => {{
                if (word.startsWith('http://') || word.startsWith('https://')) {{
                    return `<a href="${{word}}" target="_blank" rel="noopener">${{word}}</a>`;
                }}
                return word;
            }}).join(' ');
        }}

        // Format text for display: escape HTML, linkify URLs, preserve newlines
        function formatTextForDisplay(text) {{
            const escaped = escapeHtml(text);
            const linked = linkify(escaped);
            const newlineChar = String.fromCharCode(10);
            return linked.split(newlineChar).join('<br>');
        }}

        // ===== Modal Management =====
        
        function openModal(title, content) {{
            const modal = document.getElementById('transcript-modal');
            const modalTitle = document.getElementById('modal-title');
            const modalContent = document.getElementById('modal-content');
            
            modalTitle.textContent = title;
            modalContent.innerHTML = content;
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }}

        function closeModal() {{
            const modal = document.getElementById('transcript-modal');
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }}

        function openShowNotes(episodeId) {{
            const episode = episodeDescriptions[episodeId];
            if (!episode) {{
                console.error('Episode not found:', episodeId);
                return;
            }}
            
            const description = episode.description || 'No show notes available.';
            const formatted = formatTextForDisplay(description);
            openModal('Show Notes: ' + episode.title, `<div class="show-notes-content">${{formatted}}</div>`);
        }}

        function openTranscript(title, transcriptUrl) {{
            openModal('Transcript: ' + title, '<div class="transcript-loading">Loading transcript...</div>');
            
            fetch(transcriptUrl)
                .then(r => {{
                    if (!r.ok) throw new Error('Failed to load');
                    return r.text();
                }})
                .then(text => {{
                    const formatted = formatTextForDisplay(text);
                    document.getElementById('modal-content').innerHTML = `<div class="transcript-text">${{formatted}}</div>`;
                }})
                .catch(err => {{
                    document.getElementById('modal-content').innerHTML = '<div class="transcript-error">Could not load transcript</div>';
                }});
        }}

        // Modal event listeners
        document.getElementById('transcript-modal').addEventListener('click', (e) => {{
            if (e.target.classList.contains('modal-overlay')) closeModal();
        }});
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});

        // ===== Audio Player Management =====
        
        function updateButtonState(episodeId, isPlaying) {{
            const btn = document.getElementById('btn-' + episodeId);
            if (!btn) return;
            
            const isCompact = btn.classList.contains('play-button');
            const isPrimary = btn.classList.contains('btn-primary');
            
            if (isPlaying) {{
                btn.textContent = isCompact ? '⏸' : '⏸ Pause';
            }} else {{
                if (isCompact) btn.textContent = '▶';
                else if (isPrimary) btn.textContent = '▶ Play Episode';
                else btn.textContent = '▶ Listen';
            }}
        }}

        function attachAudioListeners(episodeId) {{
            const audio = document.getElementById('audio-' + episodeId);
            if (!audio) return;
            
            audio.addEventListener('play', () => {{
                // Stop other audio if playing
                if (currentAudio && currentAudio !== audio && !currentAudio.paused) {{
                    currentAudio.pause();
                    const prevPlayer = document.getElementById('player-' + currentPlayerId);
                    if (prevPlayer) prevPlayer.classList.remove('active');
                }}
                
                // Update UI
                updateButtonState(episodeId, true);
                const player = document.getElementById('player-' + episodeId);
                if (player) player.classList.add('active');
                currentAudio = audio;
                currentPlayerId = episodeId;
            }});
            
            audio.addEventListener('pause', () => updateButtonState(episodeId, false));
            audio.addEventListener('ended', () => updateButtonState(episodeId, false));
        }}

        function togglePlayer(episodeId, audioUrl) {{
            const player = document.getElementById('player-' + episodeId);
            const audio = document.getElementById('audio-' + episodeId);
            
            // Toggle if same episode
            if (currentPlayerId === episodeId) {{
                audio.paused ? audio.play() : audio.pause();
                return;
            }}
            
            // Stop current audio
            if (currentAudio && !currentAudio.paused) {{
                currentAudio.pause();
                const prevPlayer = document.getElementById('player-' + currentPlayerId);
                if (prevPlayer) prevPlayer.classList.remove('active');
            }}
            
            // Play new audio
            player.classList.add('active');
            audio.play();
        }}

        // ===== Feed Parsing =====
        
        function parseEpisode(item, index) {{
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
                if (localName === 'duration') duration = child.textContent;
                if (localName === 'image' && child.hasAttribute('href')) imageUrl = child.getAttribute('href');
                if (localName === 'summary') summary = child.textContent;
            }}
            
                    if (!imageUrl) {{
                        const itunesImages = item.getElementsByTagName('itunes:image');
                if (itunesImages.length > 0) imageUrl = itunesImages[0].getAttribute('href');
                    }}
                    
            // Keep full description for show notes (with HTML formatting)
            const fullDescription = description;
                    
            // Create plain text version for preview
            const episodeDesc = (summary || description).replace(/<[^>]*>/g, '').trim();
                    let dateStr = '';
                    if (pubDate) {{
                        const d = new Date(pubDate);
                        dateStr = d.toLocaleDateString('en-US', {{ weekday: 'short', month: 'short', day: 'numeric' }});
                    }}
                    
                    const artStyle = imageUrl 
                        ? `background-image: url('${{imageUrl}}'); background-size: cover; background-position: center;`
                : `background: linear-gradient(135deg, #e0e0e0 0%, #c0c0c0 100%);`;
            
            return {{ title, pubDate, guid: guid || index, description: episodeDesc, fullDescription, audioUrl, duration, imageUrl, dateStr, artStyle }};
        }}

        // ===== Load and Render Episodes =====
        
        function renderLatestEpisode(episode) {{
            const transcriptUrl = transcriptBaseUrl + episode.guid + '.txt';
            const escapedTitle = episode.title.replace(/'/g, "\\\\'");
                    const escapedUrl = transcriptUrl.replace(/'/g, "\\\\'");
                    
            episodeDescriptions[episode.guid] = {{
                title: episode.title,
                description: episode.fullDescription
            }};
            
            document.getElementById('latest-episode-placeholder').innerHTML = `
                <p class="latest-label">Latest Episode</p>
                <div class="latest-episode-content">
                    <div class="episode-art" style="${{episode.artStyle}}"></div>
                    <div class="latest-episode-info">
                        <h2>${{episode.title}}</h2>
                        <p class="episode-meta">${{episode.dateStr}} · ${{episode.duration}}</p>
                        ${{episode.description ? `<p class="episode-description">${{episode.description}}</p>` : ''}}
                    </div>
                </div>
                <div class="primary-actions">
                    <button class="btn-primary" id="btn-${{episode.guid}}" onclick="togglePlayer('${{episode.guid}}', '${{episode.audioUrl}}')">▶ Play Episode</button>
                    <button class="btn-secondary" onclick="openShowNotes('${{episode.guid}}')">📝 Show Notes</button>
                    <button class="btn-secondary" onclick="openTranscript('${{escapedTitle}}', '${{escapedUrl}}')">📄 Transcript</button>
                </div>
                <div class="audio-player" id="player-${{episode.guid}}">
                    <audio id="audio-${{episode.guid}}" src="${{episode.audioUrl}}" preload="none" controls></audio>
                </div>
            `;
            
            attachAudioListeners(episode.guid);
        }}
        
        function renderEpisodeList(items) {{
            const maxEpisodes = 10;
            const episodeGuids = [];
            let episodesHtml = '';
            
            for (let i = 1; i < Math.min(items.length, maxEpisodes); i++) {{
                const ep = parseEpisode(items[i], i);
                const transcriptUrl = transcriptBaseUrl + ep.guid + '.txt';
                const escapedTitle = ep.title.replace(/'/g, "\\\\'");
                const escapedUrl = transcriptUrl.replace(/'/g, "\\\\'");
                
                episodeDescriptions[ep.guid] = {{
                    title: ep.title,
                    description: ep.fullDescription
                }};
                
                episodeGuids.push(ep.guid);
                
                episodesHtml += `
                    <div class="episode">
                            <div class="episode-row">
                            <div class="episode-art" style="${{ep.artStyle}}"></div>
                                <div class="episode-info">
                                <h3>${{ep.title}}</h3>
                                <p class="episode-meta">${{ep.dateStr}} · ${{ep.duration}}</p>
                                    </div>
                            <div class="episode-actions">
                                <button class="play-button" id="btn-${{ep.guid}}" onclick="togglePlayer('${{ep.guid}}', '${{ep.audioUrl}}')" title="Play">▶</button>
                                <button onclick="openShowNotes('${{ep.guid}}')" title="Show Notes">📝</button>
                                <button onclick="openTranscript('${{escapedTitle}}', '${{escapedUrl}}')" title="Transcript">📄</button>
                                </div>
                            </div>
                        <div class="audio-player" id="player-${{ep.guid}}">
                            <audio id="audio-${{ep.guid}}" src="${{ep.audioUrl}}" preload="none" controls></audio>
                            </div>
                        </div>
                    `;
                }}
                
                document.getElementById('episodes-list').innerHTML = episodesHtml;
            episodeGuids.forEach(guid => attachAudioListeners(guid));
        }}
        
        // Load feed and render episodes
        fetch('feed.xml')
            .then(r => r.text())
            .then(xml => {{
                const parser = new DOMParser();
                const doc = parser.parseFromString(xml, 'text/xml');
                const items = doc.querySelectorAll('item');
                
                if (items.length === 0) return;
                
                renderLatestEpisode(parseEpisode(items[0], 0));
                renderEpisodeList(items);
            }})
            .catch(err => console.error('Feed error:', err));
    </script>
</body>
</html>'''
    
    return html


def generate_about_html(config: dict) -> str:
    """Generate the about.html page showing current configuration.
    
    Args:
        config: Full configuration dictionary.
    
    Returns:
        HTML string for about.html.
    """
    podcast = config.get("podcast", {})
    vibe = config.get("vibe", {})
    sources_config = config.get("sources", {})
    tts_root_config = config.get("tts", {})
    
    title = podcast.get("title", "Vibecast")
    short_title = title.split(":")[0].strip() if ":" in title else title
    tagline = podcast.get("tagline", "A daily podcast of good news and good vibes.")
    author = podcast.get("author", "")
    author_url = podcast.get("author_url", "")
    github_url = podcast.get("github_url") or config.get("github_url", "https://github.com/domcritchlow/vibecast")
    
    # Vibe configuration
    mood = vibe.get("mood", {})
    mood_primary = mood.get("primary", "uplifting")
    mood_secondary = mood.get("secondary", "optimistic")
    voice_persona = vibe.get("voice_persona", {})
    persona_name = voice_persona.get("name", "Your daily companion")
    personality_traits = voice_persona.get("personality", [])
    embrace = vibe.get("embrace", {})
    embrace_topics = embrace.get("topics", [])
    avoid_topics = vibe.get("avoid", {}).get("topics", [])
    
    # TTS configuration
    tts_provider = tts_root_config.get("provider", "openai")
    if tts_provider == "openai":
        openai_tts = tts_root_config.get("openai", {})
        tts_voice = openai_tts.get("voice", "nova")
    else:
        elevenlabs_tts = tts_root_config.get("elevenlabs", {})
        tts_voice = elevenlabs_tts.get("voice_id", "rachel")
    
    # Sources
    sources_list = []
    for source in sources_config.get("rss_feeds", []):
        if source.get("enabled", True):
            sources_list.append(source.get("name", source.get("url", "Unknown")))
    
    # Author link
    if author and author_url:
        author_html = f'<a href="{author_url}" target="_blank" rel="noopener">{author}</a>'
    elif author:
        author_html = author
    else:
        author_html = "the Vibecast team"
    
    # Build personality traits HTML
    traits_html = ""
    if personality_traits:
        traits_items = "".join([f"<li>{trait}</li>" for trait in personality_traits])
        traits_html = f"<ul class='traits-list'>{traits_items}</ul>"
    
    # Build embrace topics HTML
    embrace_html = ""
    if embrace_topics:
        embrace_items = "".join([f"<li>{topic}</li>" for topic in embrace_topics])
        embrace_html = f"<ul class='topics-list'>{embrace_items}</ul>"
    
    # Build avoid topics HTML
    avoid_html = ""
    if avoid_topics:
        avoid_items = "".join([f"<li>{topic}</li>" for topic in avoid_topics])
        avoid_html = f"<ul class='topics-list'>{avoid_items}</ul>"
    
    # Build sources HTML
    sources_html = ""
    if sources_list:
        sources_items = "".join([f"<li>{source}</li>" for source in sources_list])
        sources_html = f"<ul class='sources-list'>{sources_items}</ul>"
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About This Show — {short_title}</title>
    <style>
        :root {{
            --font-serif: 'Playfair Display', Georgia, serif;
            --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            --color-text: #1a1a1a;
            --color-text-light: #666;
            --color-bg: #fafafa;
            --color-border: #e0e0e0;
            --color-accent: #2c5282;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: var(--font-sans);
            color: var(--color-text);
            background: white;
            line-height: 1.6;
        }}

        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 64px 24px;
        }}

        header {{
            text-align: center;
            margin-bottom: 64px;
        }}

        header h1 {{
            font-family: var(--font-serif);
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 12px;
            line-height: 1.2;
        }}

        header .tagline {{
            font-size: 1.125rem;
            color: var(--color-text-light);
            margin-bottom: 24px;
        }}

        header .back-link {{
            display: inline-block;
            color: var(--color-accent);
            text-decoration: none;
            font-size: 0.9rem;
            transition: opacity 0.2s;
        }}

        header .back-link:hover {{
            opacity: 0.7;
        }}

        section {{
            margin-bottom: 48px;
        }}

        h2 {{
            font-family: var(--font-serif);
            font-size: 1.75rem;
            font-weight: 600;
            margin-bottom: 16px;
        }}

        p {{
            font-size: 1.0625rem;
            line-height: 1.7;
            margin-bottom: 16px;
            color: var(--color-text);
        }}

        .config-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }}

        .config-item {{
            padding: 20px;
            background: var(--color-bg);
            border: 1px solid var(--color-border);
            border-radius: 8px;
        }}

        .config-label {{
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--color-text-light);
            margin-bottom: 8px;
        }}

        .config-value {{
            font-size: 1.125rem;
            color: var(--color-text);
        }}

        .traits-list, .topics-list, .sources-list {{
            list-style: none;
            padding-left: 0;
        }}

        .traits-list li, .topics-list li, .sources-list li {{
            padding: 8px 0;
            padding-left: 24px;
            position: relative;
        }}

        .traits-list li:before, .topics-list li:before, .sources-list li:before {{
            content: "•";
            position: absolute;
            left: 8px;
            color: var(--color-accent);
        }}

        footer {{
            padding-top: 48px;
            margin-top: 64px;
            border-top: 1px solid var(--color-border);
            text-align: center;
            font-size: 0.9rem;
            color: var(--color-text-light);
        }}

        .footer-links {{
            margin-top: 16px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}

        .footer-links a {{
            color: var(--color-text);
            text-decoration: none;
            transition: color 0.2s;
        }}

        .footer-links a:hover {{
            color: var(--color-accent);
        }}

        .footer-links span {{
            color: var(--color-text-light);
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 48px 20px;
            }}

            header h1 {{
                font-size: 2rem;
            }}

            h2 {{
                font-size: 1.5rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>About This Show</h1>
            <p class="tagline">{tagline}</p>
            <a href="index.html" class="back-link">← Back to episodes</a>
        </header>

        <main>
            <section>
                <h2>The Vibe</h2>
                <div class="config-grid">
                    <div class="config-item">
                        <div class="config-label">Mood</div>
                        <div class="config-value">{mood_primary.capitalize()}, {mood_secondary.capitalize()}</div>
                    </div>
                    <div class="config-item">
                        <div class="config-label">Voice Persona</div>
                        <div class="config-value">{persona_name}</div>
                    </div>
                    <div class="config-item">
                        <div class="config-label">Narrated By</div>
                        <div class="config-value">{tts_voice.capitalize()}</div>
                    </div>
                </div>
                {f"<h3>Personality</h3>{traits_html}" if personality_traits else ""}
            </section>

            {f"<section><h2>Topics We Cover</h2>{embrace_html}</section>" if embrace_topics else ""}
            
            {f"<section><h2>Topics We Avoid</h2>{avoid_html}</section>" if avoid_topics else ""}

            <section>
                <h2>Our Sources</h2>
                <p>Every episode is curated from carefully selected news sources to bring you the best content:</p>
                {sources_html}
            </section>

            <section>
                <h2>How It's Made</h2>
                <p>This podcast is generated daily using AI technology. Here's how it works:</p>
                <ol style="padding-left: 24px; line-height: 1.8;">
                    <li>We fetch the latest articles from our trusted sources</li>
                    <li>AI filters and selects the most relevant content based on your preferences</li>
                    <li>A script is generated that matches your chosen vibe and personality</li>
                    <li>The script is converted to natural-sounding speech using {tts_provider.capitalize()} TTS</li>
                    <li>Everything is packaged into a podcast episode, ready for your morning</li>
                </ol>
            </section>
        </main>

        <footer>
            <p>Made by {author_html}</p>
            <nav class="footer-links">
                <a href="index.html">Home</a>
                <span>·</span>
                <a href="docs.html">About Vibecast</a>
            </nav>
        </footer>
    </div>
</body>
</html>'''
    
    return html


def generate_docs_html(config: dict) -> str:
    """Generate the docs.html page with project documentation.
    
    Args:
        config: Full configuration dictionary.
    
    Returns:
        HTML string for docs.html.
    """
    podcast = config.get("podcast", {})
    title = podcast.get("title", "Vibecast")
    short_title = title.split(":")[0].strip() if ":" in title else title
    author = podcast.get("author", "")
    author_url = podcast.get("author_url", "")
    github_url = podcast.get("github_url") or config.get("github_url", "https://github.com/domcritchlow/vibecast")
    
    # Author link
    if author and author_url:
        author_html = f'<a href="{author_url}" target="_blank" rel="noopener">{author}</a>'
    elif author:
        author_html = author
    else:
        author_html = "the Vibecast team"
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About Vibecast — {short_title}</title>
    <style>
        :root {{
            --font-serif: 'Playfair Display', Georgia, serif;
            --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            --color-text: #1a1a1a;
            --color-text-light: #666;
            --color-bg: #fafafa;
            --color-border: #e0e0e0;
            --color-accent: #2c5282;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: var(--font-sans);
            color: var(--color-text);
            background: white;
            line-height: 1.6;
        }}

        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 64px 24px;
        }}

        header {{
            text-align: center;
            margin-bottom: 64px;
        }}

        header h1 {{
            font-family: var(--font-serif);
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 12px;
            line-height: 1.2;
        }}

        header .subtitle {{
            font-size: 1.125rem;
            color: var(--color-text-light);
            margin-bottom: 24px;
        }}

        header .back-link {{
            display: inline-block;
            color: var(--color-accent);
            text-decoration: none;
            font-size: 0.9rem;
            transition: opacity 0.2s;
        }}

        header .back-link:hover {{
            opacity: 0.7;
        }}

        section {{
            margin-bottom: 48px;
        }}

        h2 {{
            font-family: var(--font-serif);
            font-size: 1.75rem;
            font-weight: 600;
            margin-bottom: 16px;
        }}

        h3 {{
            font-family: var(--font-serif);
            font-size: 1.375rem;
            font-weight: 600;
            margin-bottom: 12px;
            margin-top: 24px;
        }}

        p {{
            font-size: 1.0625rem;
            line-height: 1.7;
            margin-bottom: 16px;
            color: var(--color-text);
        }}

        code {{
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
            background: var(--color-bg);
            padding: 2px 6px;
            border-radius: 3px;
            border: 1px solid var(--color-border);
        }}

        pre {{
            background: var(--color-bg);
            border: 1px solid var(--color-border);
            border-radius: 6px;
            padding: 16px;
            overflow-x: auto;
            margin-bottom: 16px;
        }}

        pre code {{
            background: none;
            border: none;
            padding: 0;
        }}

        ol, ul {{
            padding-left: 24px;
            margin-bottom: 16px;
        }}

        li {{
            margin-bottom: 8px;
            line-height: 1.7;
        }}

        .cta-box {{
            background: var(--color-bg);
            border: 2px solid var(--color-accent);
            border-radius: 8px;
            padding: 24px;
            margin: 32px 0;
            text-align: center;
        }}

        .cta-box p {{
            margin-bottom: 16px;
        }}

        .cta-button {{
            display: inline-block;
            background: var(--color-accent);
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            transition: opacity 0.2s;
        }}

        .cta-button:hover {{
            opacity: 0.9;
        }}

        footer {{
            padding-top: 48px;
            margin-top: 64px;
            border-top: 1px solid var(--color-border);
            text-align: center;
            font-size: 0.9rem;
            color: var(--color-text-light);
        }}

        .footer-links {{
            margin-top: 16px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}

        .footer-links a {{
            color: var(--color-text);
            text-decoration: none;
            transition: color 0.2s;
        }}

        .footer-links a:hover {{
            color: var(--color-accent);
        }}

        .footer-links span {{
            color: var(--color-text-light);
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 48px 20px;
            }}

            header h1 {{
                font-size: 2rem;
            }}

            h2 {{
                font-size: 1.5rem;
            }}

            h3 {{
                font-size: 1.25rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>About Vibecast</h1>
            <p class="subtitle">Your News, Your Way</p>
            <a href="index.html" class="back-link">← Back to episodes</a>
        </header>

        <main>
            <section>
                <h2>What is Vibecast?</h2>
                <p>Vibecast is an open-source AI-powered podcast generator that creates personalized daily news briefings. Instead of generic news, you get a podcast tailored to your interests, mood, and preferred sources—delivered fresh every morning.</p>
                <p>Built with Python, it combines RSS feed aggregation, OpenAI's GPT models for content generation, and text-to-speech synthesis to create production-ready podcast episodes automatically.</p>
            </section>

            <div class="cta-box">
                <p><strong>Want to create your own personalized podcast?</strong></p>
                <a href="{github_url}" class="cta-button" target="_blank" rel="noopener">Get Started on GitHub →</a>
            </div>

            <section>
                <h2>Features</h2>
                <ul>
                    <li><strong>Fully Customizable:</strong> Choose your news sources, topics, mood, and voice persona</li>
                    <li><strong>AI-Powered:</strong> GPT-4 generates natural, conversational scripts from your selected content</li>
                    <li><strong>Multiple TTS Options:</strong> Support for OpenAI TTS and ElevenLabs voices</li>
                    <li><strong>Automated Publishing:</strong> Generates podcast RSS feed and a beautiful website automatically</li>
                    <li><strong>Cloud Storage:</strong> Integrates with Cloudflare R2 for media hosting</li>
                    <li><strong>GitHub Actions Ready:</strong> Deploy once, runs daily automatically</li>
                </ul>
            </section>

            <section>
                <h2>Quick Start</h2>
                
                <h3>1. Clone the Repository</h3>
                <pre><code>git clone {github_url}.git
cd vibecast</code></pre>

                <h3>2. Install Dependencies</h3>
                <pre><code>python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt</code></pre>

                <h3>3. Configure Your Podcast</h3>
                <p>Edit <code>podcast/config.yaml</code> to customize:</p>
                <ul>
                    <li><strong>Podcast metadata:</strong> Title, author, description</li>
                    <li><strong>Vibe settings:</strong> Mood, personality, voice persona</li>
                    <li><strong>Content preferences:</strong> Topics to embrace or avoid</li>
                    <li><strong>RSS sources:</strong> Add your favorite news feeds</li>
                    <li><strong>TTS provider:</strong> OpenAI or ElevenLabs</li>
                </ul>

                <h3>4. Set Up API Keys</h3>
                <p>Create a <code>.env</code> file with your credentials:</p>
                <pre><code>OPENAI_API_KEY=your_key_here
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key</code></pre>

                <h3>5. Generate Your First Episode</h3>
                <pre><code>python -m podcast.run_daily</code></pre>

                <h3>6. Deploy to GitHub Pages</h3>
                <p>Push to GitHub and enable GitHub Actions. The workflow will automatically generate new episodes daily and publish to GitHub Pages.</p>
            </section>

            <section>
                <h2>How It Works</h2>
                <ol>
                    <li><strong>Content Collection:</strong> Fetches latest articles from your configured RSS feeds</li>
                    <li><strong>Smart Filtering:</strong> AI analyzes articles and selects the best content based on your preferences</li>
                    <li><strong>Script Generation:</strong> GPT-4 writes a natural, conversational script in your chosen voice and mood</li>
                    <li><strong>Text-to-Speech:</strong> Converts the script to high-quality audio using your selected voice</li>
                    <li><strong>Publishing:</strong> Uploads audio, generates RSS feed, creates show notes, and updates the website</li>
                    <li><strong>Automation:</strong> Runs daily via GitHub Actions (or your preferred scheduler)</li>
                </ol>
            </section>

            <section>
                <h2>Tech Stack</h2>
                <ul>
                    <li><strong>Python 3.9+</strong> — Core application</li>
                    <li><strong>OpenAI GPT-4</strong> — Content generation and filtering</li>
                    <li><strong>OpenAI TTS / ElevenLabs</strong> — Text-to-speech synthesis</li>
                    <li><strong>Cloudflare R2</strong> — Media storage and CDN</li>
                    <li><strong>GitHub Actions</strong> — Automation and CI/CD</li>
                    <li><strong>GitHub Pages</strong> — Free hosting for your podcast website</li>
                </ul>
            </section>

            <section>
                <h2>Configuration</h2>
                <p>The <code>podcast/config.yaml</code> file is the heart of your podcast. Here's what you can customize:</p>
                
                <h3>Podcast Identity</h3>
                <ul>
                    <li>Title, tagline, author, email</li>
                    <li>Categories and language</li>
                    <li>Artwork and branding</li>
                </ul>

                <h3>Voice & Personality</h3>
                <ul>
                    <li>Mood (uplifting, serious, casual, etc.)</li>
                    <li>Personality traits (witty, educational, conversational)</li>
                    <li>Voice persona name and characteristics</li>
                </ul>

                <h3>Content Curation</h3>
                <ul>
                    <li>Topics to embrace (technology, science, climate, etc.)</li>
                    <li>Topics to avoid (politics, crime, etc.)</li>
                    <li>Preferred news sources (RSS feeds)</li>
                    <li>Story selection criteria</li>
                </ul>

                <h3>Technical Settings</h3>
                <ul>
                    <li>TTS provider and voice selection</li>
                    <li>Episode duration (target minutes)</li>
                    <li>Cloud storage configuration</li>
                    <li>Publishing schedule</li>
                </ul>
            </section>

            <section>
                <h2>Support & Community</h2>
                <p>Vibecast is open source and welcomes contributions!</p>
                <ul>
                    <li><strong>GitHub:</strong> <a href="{github_url}" target="_blank" rel="noopener">{github_url}</a></li>
                    <li><strong>Issues:</strong> Report bugs or request features on GitHub</li>
                    <li><strong>Pull Requests:</strong> Contributions are always welcome</li>
                </ul>
            </section>

            <section>
                <h2>License</h2>
                <p>Vibecast is released under the MIT License. You're free to use, modify, and distribute it for any purpose.</p>
            </section>
        </main>

        <footer>
            <p>Made by {author_html}</p>
            <nav class="footer-links">
                <a href="index.html">Home</a>
                <span>·</span>
                <a href="about.html">About This Show</a>
            </nav>
        </footer>
    </div>
</body>
</html>'''
    
    return html


def save_index_html(config: dict, site_dir: Path) -> None:
    """Generate and save all HTML pages to the site directory.
    
    Args:
        config: Full configuration dictionary.
        site_dir: Path to the site directory.
    """
    # Generate and save index.html
    index_html = generate_index_html(config)
    index_path = site_dir / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    
    # Generate and save about.html
    about_html = generate_about_html(config)
    about_path = site_dir / "about.html"
    with open(about_path, "w", encoding="utf-8") as f:
        f.write(about_html)
    
    # Generate and save docs.html
    docs_html = generate_docs_html(config)
    docs_path = site_dir / "docs.html"
    with open(docs_path, "w", encoding="utf-8") as f:
        f.write(docs_html)

