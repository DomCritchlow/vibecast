"""Tests for state pruning and legacy-state migration."""

from datetime import datetime, timedelta

from podcast.run_daily import prune_state


def test_prune_state_drops_old_urls():
    now = datetime.now()
    state = {
        "url_timestamps": {
            "https://x/old": (now - timedelta(days=120)).isoformat(),
            "https://x/new": (now - timedelta(days=5)).isoformat(),
            "https://x/bad": "not-a-timestamp",
        }
    }
    pruned = prune_state(state, retention_days=90)
    assert set(pruned["url_timestamps"]) == {"https://x/new"}


def test_prune_state_keeps_everything_within_window():
    now = datetime.now().isoformat()
    state = {"url_timestamps": {"https://x/a": now, "https://x/b": now}}
    assert len(prune_state(state, retention_days=90)["url_timestamps"]) == 2
