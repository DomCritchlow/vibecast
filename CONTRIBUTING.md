# Contributing to Vibecast

Thank you for your interest in contributing to Vibecast! This document will help you get started.

## 🌟 Ways to Contribute

- **🐛 Bug Reports**: Found an issue? Open a GitHub issue with steps to reproduce
- **💡 Feature Requests**: Have an idea? Describe your use case in an issue
- **🔧 Code Contributions**: PRs are welcome for bug fixes and new features
- **📚 Documentation**: Improve guides, fix typos, add examples
- **🎨 Share Configs**: Show off creative vibe configurations in Discussions
- **🎙️ Share Your Podcast**: Let us know if you deploy Vibecast!

## 🚀 Development Setup

### Prerequisites
- Python 3.9 or higher
- FFmpeg (for audio processing)
- Git

### Getting Started

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/vibecast.git
   cd vibecast
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Test your setup**
   ```bash
   # Dry run (no API calls or costs)
   python -m podcast.run_daily --dry-run -v
   ```

## 🔨 Making Changes

### Code Style
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and modular

### Testing Locally
```bash
# Dry run to test without API costs
python -m podcast.run_daily --dry-run -v

# Full run (costs ~$0.05-0.15 per episode)
python -m podcast.run_daily -v
```

### Project Structure
```
vibecast/
├── podcast/
│   ├── run_daily.py      # Main orchestrator
│   ├── writer.py         # AI script generation
│   ├── sources/          # Content fetchers (RSS, weather, etc.)
│   ├── tts/              # TTS providers (OpenAI, ElevenLabs)
│   ├── artwork/          # Episode artwork (DALL-E generation)
│   ├── templates/        # Jinja2 HTML templates
│   │   ├── base.html     # Shared layout
│   │   ├── index.html    # Homepage
│   │   ├── about.html    # About Riso
│   │   └── docs.html     # Documentation
│   ├── rss_feed.py       # RSS feed generation
│   └── site_generator.py # Template rendering
├── docs/                 # Generated site
│   └── assets/
│       ├── css/          # Design system (tokens, components, pages)
│       ├── textures/     # SVG textures (halftone, grain, etc.)
│       └── images/       # Host image, artwork
└── .github/workflows/    # GitHub Actions automation
```

## 📝 Pull Request Guidelines

1. **Keep PRs focused**: One feature or fix per PR
2. **Write clear descriptions**: Explain what and why
3. **Test thoroughly**: Ensure your changes work with dry-run
4. **Update documentation**: If you change behavior, update docs
5. **Follow existing patterns**: Match the style of surrounding code

### PR Checklist
- [ ] Code follows project style
- [ ] Changes tested locally with `--dry-run`
- [ ] Documentation updated (if needed)
- [ ] No sensitive data (API keys, credentials) in commits
- [ ] Commit messages are clear and descriptive

## 🆕 Adding New Features

### New TTS Provider
1. Create a new file in `podcast/tts/` (e.g., `my_provider.py`)
2. Extend `TTSProvider` base class from `tts/base.py`
3. Implement `synthesize()` and `get_voice_id()` methods
4. Register in `tts/__init__.py`

### New Content Source
1. Create a new file in `podcast/sources/` (e.g., `my_source.py`)
2. Extend `ContentSource` base class from `sources/base.py`
3. Implement `fetch()` method that returns `ContentItem` objects
4. Add configuration section in `config.yaml`

### New Audio Processing Preset
1. Add preset to `audio_processing.py`
2. Document in `AUDIO_PROCESSING_GUIDE.md`
3. Update `config.yaml` with new preset option

### Modifying Templates & Styles

**Templates** live in `podcast/templates/`:
- `base.html` — Shared layout (nav, footer, scripts)
- `index.html` — Homepage with episode player
- `about.html` — Meet Bento page
- `docs.html` — Documentation

**CSS Design System** in `docs/assets/css/`:
- `design-system.css` — Tokens (`:root` variables for colors, spacing, fonts)
- `components.css` — Reusable UI (buttons, cards, audio players)
- `pages.css` — Page-specific layouts and hero sections

**Textures** in `docs/assets/textures/`:
- SVG files with `feTurbulence` for organic noise
- Applied via CSS `background-image` and `mix-blend-mode`

To regenerate the site after template changes:
```bash
python -c "
import yaml
from pathlib import Path
from podcast.site_generator import save_site_pages

with open('podcast/config.yaml') as f:
    config = yaml.safe_load(f)
save_site_pages(config, Path('docs'))
"
```

### Generating New Podcast Artwork

Use the artwork generation script:
```bash
python scripts/generate_podcast_cover.py
```

This creates a risograph-style cover and saves it to `docs/assets/images/podcast-cover.png`.

## 🐛 Reporting Bugs

When reporting bugs, please include:

- **Description**: What happened vs. what you expected
- **Steps to reproduce**: Exact steps to trigger the bug
- **Environment**: OS, Python version, relevant config settings
- **Logs**: Error messages or relevant output
- **Dry-run behavior**: Does it happen in `--dry-run` mode?

## 💬 Questions or Ideas?

- **GitHub Discussions**: For questions, ideas, and showcasing your podcast
- **GitHub Issues**: For bugs and feature requests
- **Pull Requests**: For code contributions

## 📜 Code of Conduct

Be respectful, inclusive, and constructive. We're building this together to help people create amazing personalized podcasts!

## 🎯 Good First Issues

Look for issues labeled `good first issue` if you're new to the project. These are typically:
- Documentation improvements
- Small bug fixes
- Adding example configurations
- Improving error messages

## 🙏 Thank You!

Every contribution makes Vibecast better. Whether it's a typo fix, a new feature, or just spreading the word—thank you for being part of this project!

