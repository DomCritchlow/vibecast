"""Tests for content filtering and selection."""

from podcast.sources.base import ContentItem, filter_items, select_items


def make_item(title, source="Source A", url=None, tags=None, score=0.0):
    return ContentItem(
        title=title,
        url=url or f"https://example.com/{title}",
        source=source,
        tags=tags or [],
        score=score,
    )


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


def test_filter_adds_boosts_to_trust_score():
    items = [
        make_item("Plain story from trusted source", score=0.95),
        make_item("A research story from untrusted source", score=0.5),
    ]
    result = filter_items(items, block_keywords=[], boost_keywords=["research"], used_urls=set())
    # 0.5 trust + 1.0 boost beats 0.95 trust + 0 boosts
    assert result[0].title == "A research story from untrusted source"
    assert result[0].score == 1.5
    assert result[1].score == 0.95


def test_select_items_respects_source_diversity():
    items = [
        make_item("A1", source="A"),
        make_item("A2", source="A"),
        make_item("A3", source="A"),
        make_item("B1", source="B"),
    ]
    result = select_items(items, max_items=3, max_per_source=2)
    assert [i.title for i in result] == ["A1", "A2", "B1"]


def test_variety_slot_swaps_in_lowest_ranked_position():
    items = [
        make_item("AI1", source="A"),
        make_item("AI2", source="B"),
        make_item("AI3", source="C"),
        make_item("Fun1", source="V", tags=["variety"]),
    ]
    result = select_items(
        items, max_items=3, max_per_source=2, variety_tags=["variety"], variety_slots=1
    )
    # Fun1 replaces the last (lowest-scored) non-variety pick
    assert [i.title for i in result] == ["AI1", "AI2", "Fun1"]


def test_variety_slot_not_duplicated_when_already_selected():
    items = [
        make_item("Fun1", source="V", tags=["variety"]),
        make_item("AI1", source="A"),
        make_item("Fun2", source="W", tags=["variety"]),
    ]
    result = select_items(
        items, max_items=2, max_per_source=2, variety_tags=["variety"], variety_slots=1
    )
    # Fun1 already made the cut naturally; no swap should happen
    assert [i.title for i in result] == ["Fun1", "AI1"]


def test_variety_slot_noop_without_candidates():
    items = [make_item("AI1", source="A"), make_item("AI2", source="B")]
    result = select_items(
        items, max_items=2, max_per_source=2, variety_tags=["variety"], variety_slots=1
    )
    assert [i.title for i in result] == ["AI1", "AI2"]


def test_variety_slot_respects_max_per_source():
    items = [
        make_item("AI1", source="A"),
        make_item("Fun1", source="V", tags=["variety"]),
        make_item("Fun2", source="V", tags=["variety"]),
        make_item("Fun3", source="W", tags=["variety"]),
        make_item("AI2", source="B"),
        make_item("AI3", source="C"),
    ]
    result = select_items(
        items, max_items=4, max_per_source=1, variety_tags=["variety"], variety_slots=2
    )
    # Fun1 selected naturally; second slot must come from W (V is at cap)
    titles = [i.title for i in result]
    assert "Fun1" in titles and "Fun3" in titles
    assert "Fun2" not in titles
