"""Tests for reading list sorting with mixed date types."""

from datetime import UTC, datetime

from podcast.sources.reading_list import ReadingListItem, _sort_key


def make(title, published):
    return ReadingListItem(
        title=title, url=f"https://x/{title}", source="Blog", published=published
    )


def test_sort_key_handles_mixed_none_naive_and_aware():
    items = [
        make("none", None),
        make("naive", datetime(2026, 7, 1)),
        make("aware", datetime(2026, 7, 2, tzinfo=UTC)),
    ]
    # Regression: this used to raise TypeError (datetime vs str comparison)
    items.sort(key=_sort_key, reverse=True)
    assert [i.title for i in items] == ["aware", "naive", "none"]
