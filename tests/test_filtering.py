"""Tests for content filtering and selection."""

from podcast.sources.base import ContentItem, filter_items, select_items


def make_item(title, source="Source A", url=None):
    return ContentItem(title=title, url=url or f"https://example.com/{title}", source=source)


def test_filter_blocks_keywords():
    items = [make_item("A peaceful discovery"), make_item("A terrible war story")]
    result = filter_items(items, block_keywords=["war"], boost_keywords=[], used_urls=set())
    assert [i.title for i in result] == ["A peaceful discovery"]


def test_filter_skips_used_urls():
    items = [make_item("Fresh"), make_item("Stale")]
    used = {"https://example.com/Stale"}
    result = filter_items(items, block_keywords=[], boost_keywords=[], used_urls=used)
    assert [i.title for i in result] == ["Fresh"]


def test_filter_boosts_and_sorts():
    items = [make_item("Plain story"), make_item("A research breakthrough")]
    result = filter_items(
        items, block_keywords=[], boost_keywords=["research", "breakthrough"], used_urls=set()
    )
    assert result[0].title == "A research breakthrough"
    assert result[0].score == 2.0


def test_select_items_respects_source_diversity():
    items = [
        make_item("A1", source="A"),
        make_item("A2", source="A"),
        make_item("A3", source="A"),
        make_item("B1", source="B"),
    ]
    result = select_items(items, max_items=3, max_per_source=2)
    assert [i.title for i in result] == ["A1", "A2", "B1"]
