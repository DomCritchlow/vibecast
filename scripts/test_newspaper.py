#!/usr/bin/env python3
"""Test newspaper PDF generation with sample data."""

import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from podcast.newspaper import generate_newspaper_html, generate_newspaper_pdf
from podcast.sources.base import ContentItem


def create_sample_data():
    """Create sample episode data for testing."""
    
    # Sample stories
    items = [
        ContentItem(
            title="OpenAI Releases New Reasoning Model",
            url="https://openai.com/news/sample",
            source="OpenAI News",
            summary="OpenAI has unveiled a new reasoning model that shows significant improvements in complex problem-solving tasks. The model demonstrates enhanced chain-of-thought capabilities and can break down multi-step problems with greater accuracy. Early tests show improvements across mathematics, coding, and scientific reasoning benchmarks.",
            published=datetime.now(),
            tags=["ai", "research"],
            score=0.95,
        ),
        ContentItem(
            title="NASA's James Webb Telescope Discovers Ancient Galaxy",
            url="https://nasa.gov/news/sample",
            source="NASA Science",
            summary="The James Webb Space Telescope has identified one of the oldest galaxies ever observed, dating back to just 300 million years after the Big Bang. The discovery challenges existing models of early galaxy formation and provides new insights into the universe's evolution.",
            published=datetime.now(),
            tags=["space", "science"],
            score=0.90,
        ),
        ContentItem(
            title="Breakthrough in Quantum Computing Error Correction",
            url="https://research.google/sample",
            source="Google Research",
            summary="Researchers have demonstrated a new quantum error correction technique that significantly extends the coherence time of quantum bits. This advancement brings practical quantum computers closer to reality.",
            published=datetime.now(),
            tags=["quantum", "computing"],
            score=0.85,
        ),
        ContentItem(
            title="Solar Energy Costs Drop Below Fossil Fuels Globally",
            url="https://energy.gov/sample",
            source="MIT Technology Review",
            summary="New analysis shows solar energy has become the cheapest source of electricity in most major markets worldwide, marking a historic shift in energy economics.",
            published=datetime.now(),
            tags=["energy", "climate"],
            score=0.80,
        ),
    ]
    
    # Sample reading list
    class ReadingListItem(ContentItem):
        def __init__(self, *args, author="", description="", **kwargs):
            super().__init__(*args, **kwargs)
            self.author = author
            self.description = description
    
    reading_items = [
        ReadingListItem(
            title="Understanding Modern System Design",
            url="https://blog.bytebytego.com/sample",
            source="ByteByteGo Newsletter",
            author="Alex Xu",
            description="A deep dive into distributed systems architecture, covering load balancing, caching strategies, and database sharding patterns used by major tech companies.",
            published=datetime.now(),
        ),
        ReadingListItem(
            title="The State of AI Research in 2026",
            url="https://importai.substack.com/sample",
            source="Import AI",
            author="Jack Clark",
            description="This week's roundup covers breakthrough papers in multimodal learning, new benchmarks for AI safety, and emerging trends in open-source model development.",
            published=datetime.now(),
        ),
    ]
    
    weather_text = "Clear skies with a high of 68°F (20°C). Light breeze from the west. Perfect day for a morning walk."
    
    return items, reading_items, weather_text


def main():
    """Generate test newspaper."""
    print("Generating test newspaper...")
    print()
    
    # Load config
    from podcast.run_daily import load_config
    
    try:
        config = load_config()
    except FileNotFoundError:
        print("Error: Could not find config.yaml")
        print("Make sure you're running from the project root:")
        print("  python scripts/test_newspaper.py")
        return 1
    
    # Create sample data
    items, reading_items, weather_text = create_sample_data()
    
    # Generate HTML first (for quick preview)
    print("1. Generating HTML preview...")
    
    # Use the default podcast artwork
    docs_dir = Path(__file__).parent.parent / "docs"
    default_artwork = docs_dir / "artwork.png"
    
    # Convert to relative path for HTML
    if default_artwork.exists():
        artwork_path = f"../artwork.png"
    else:
        artwork_path = None
        print("  Warning: Default artwork not found, generating without image")
    
    html_path = generate_newspaper_html(
        date=datetime.now(),
        items=items,
        config=config,
        weather_text=weather_text,
        reading_items=reading_items,
        duration_minutes=5.2,
        episode_artwork_url=artwork_path,
        accent_color="#ff6b35",  # Burnt orange
    )
    
    if html_path:
        print(f"   HTML preview: {html_path}")
        print(f"   Open in browser: file://{html_path.absolute()}")
        print()
    
    # Generate PDF
    print("2. Generating PDF...")
    try:
        pdf_path = generate_newspaper_pdf(
            date=datetime.now(),
            items=items,
            config=config,
            weather_text=weather_text,
            reading_items=reading_items,
            duration_minutes=5.2,
            episode_artwork_url=artwork_path,
            accent_color="#ff6b35",  # Burnt orange
        )
        
        if pdf_path:
            print(f"   PDF saved: {pdf_path}")
            print(f"   Open PDF: open {pdf_path}")
            print()
            print("✅ Success! Check out your newspaper.")
            print()
            print("Next steps:")
            print("- Open the HTML in a browser to see the design")
            print("- Open the PDF to see the print version")
            print("- Edit podcast/templates/newspaper.html to customize")
            print("- See NEWSPAPER_GUIDE.md for more options")
    
    except ImportError:
        print()
        print("⚠️  WeasyPrint not installed.")
        print()
        print("To generate PDFs, install WeasyPrint:")
        print("  pip install weasyprint")
        print()
        print("Note: WeasyPrint requires system dependencies.")
        print("See NEWSPAPER_GUIDE.md for installation instructions.")
        return 1
    
    except Exception as e:
        print(f"Error generating PDF: {e}")
        print()
        print("You can still preview the HTML version above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
