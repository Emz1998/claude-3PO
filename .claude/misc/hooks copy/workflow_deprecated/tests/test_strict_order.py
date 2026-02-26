#!/usr/bin/env python3
"""Pytest tests for strict_order deliverable enforcement."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.state_manager import StateManager  # type: ignore


@pytest.fixture
def manager(tmp_path: Path) -> StateManager:
    """Provide a StateManager with a temporary state file."""
    state_path = tmp_path / "state.json"
    mgr = StateManager(state_path=state_path)
    mgr.reset()
    return mgr


def _make_deliverable(
    action: str = "read",
    pattern: str = ".*prompt\\.md$",
    strict_order: int | None = None,
    completed: bool = False,
) -> dict:
    return {
        "type": "files",
        "action": action,
        "pattern": pattern,
        "strict_order": strict_order,
        "completed": completed,
    }


# =========================================================================
# get_min_incomplete_strict_order tests
# =========================================================================


class TestGetMinIncompleteStrictOrder:
    """Tests for get_min_incomplete_strict_order method."""

    def test_returns_minimum(self, manager: StateManager):
        """Returns the smallest strict_order among incomplete items."""
        manager.set_deliverables(
            [
                _make_deliverable(strict_order=3),
                _make_deliverable(strict_order=1),
                _make_deliverable(strict_order=2),
            ]
        )
        assert manager.get_min_incomplete_strict_order() == 1

    def test_ignores_completed(self, manager: StateManager):
        """Skips completed deliverables when finding minimum."""
        manager.set_deliverables(
            [
                _make_deliverable(strict_order=1, completed=True),
                _make_deliverable(strict_order=2),
                _make_deliverable(strict_order=3),
            ]
        )
        assert manager.get_min_incomplete_strict_order() == 2

    def test_returns_none_all_done(self, manager: StateManager):
        """Returns None when all strict_order deliverables are complete."""
        manager.set_deliverables(
            [
                _make_deliverable(strict_order=1, completed=True),
                _make_deliverable(strict_order=2, completed=True),
            ]
        )
        assert manager.get_min_incomplete_strict_order() is None

    def test_returns_none_no_strict_order(self, manager: StateManager):
        """Returns None when no deliverables have strict_order set."""
        manager.set_deliverables(
            [
                _make_deliverable(strict_order=None),
                _make_deliverable(strict_order=None),
            ]
        )
        assert manager.get_min_incomplete_strict_order() is None


# =========================================================================
# get_strict_order_block_reason tests (blocking rules)
# =========================================================================


class TestStrictOrderBlocking:
    """Tests for get_strict_order_block_reason enforcement."""

    def test_allows_current_level(self, manager: StateManager):
        """Tool matching a strict_order:1 deliverable is allowed."""
        manager.set_deliverables(
            [
                _make_deliverable(
                    action="read", pattern=".*prompt\\.md$", strict_order=1
                ),
                _make_deliverable(
                    action="write", pattern=".*report\\.md$", strict_order=2
                ),
            ]
        )
        result = manager.get_strict_order_block_reason("read", "/path/prompt.md")
        assert result is None

    def test_blocks_higher_level(self, manager: StateManager):
        """Tool matching strict_order:2 is blocked while level 1 is incomplete."""
        manager.set_deliverables(
            [
                _make_deliverable(
                    action="read", pattern=".*prompt\\.md$", strict_order=1
                ),
                _make_deliverable(
                    action="write", pattern=".*report\\.md$", strict_order=2
                ),
            ]
        )
        result = manager.get_strict_order_block_reason("write", "/path/report.md")
        assert result is not None
        assert "level 1" in result

    def test_blocks_non_strict_deliverable(self, manager: StateManager):
        """Tool matching a deliverable without strict_order is blocked while strict items remain."""
        manager.set_deliverables(
            [
                _make_deliverable(
                    action="read", pattern=".*prompt\\.md$", strict_order=1
                ),
                _make_deliverable(
                    action="write", pattern=".*notes\\.md$", strict_order=None
                ),
            ]
        )
        result = manager.get_strict_order_block_reason("write", "/path/notes.md")
        assert result is not None
        assert "level 1" in result

    def test_blocks_non_deliverable_tool(self, manager: StateManager):
        """Tool not matching any deliverable is blocked while strict items remain."""
        manager.set_deliverables(
            [
                _make_deliverable(
                    action="read", pattern=".*prompt\\.md$", strict_order=1
                ),
            ]
        )
        result = manager.get_strict_order_block_reason("write", "/path/random.txt")
        assert result is not None
        assert "level 1" in result

    def test_unlocks_after_level_done(self, manager: StateManager):
        """strict_order:2 tools allowed once all level 1 items complete."""
        manager.set_deliverables(
            [
                _make_deliverable(
                    action="read",
                    pattern=".*prompt\\.md$",
                    strict_order=1,
                    completed=True,
                ),
                _make_deliverable(
                    action="write", pattern=".*report\\.md$", strict_order=2
                ),
            ]
        )
        result = manager.get_strict_order_block_reason("write", "/path/report.md")
        assert result is None

    def test_unlocks_all_after_strict_done(self, manager: StateManager):
        """All tools allowed once all strict_order deliverables are complete."""
        manager.set_deliverables(
            [
                _make_deliverable(
                    action="read",
                    pattern=".*prompt\\.md$",
                    strict_order=1,
                    completed=True,
                ),
                _make_deliverable(
                    action="write",
                    pattern=".*report\\.md$",
                    strict_order=2,
                    completed=True,
                ),
                _make_deliverable(
                    action="edit", pattern=".*other\\.md$", strict_order=None
                ),
            ]
        )
        result = manager.get_strict_order_block_reason("bash", "npm test")
        assert result is None

    def test_same_level_any_order(self, manager: StateManager):
        """Multiple deliverables at same strict_order can satisfy in any order."""
        manager.set_deliverables(
            [
                _make_deliverable(
                    action="read", pattern=".*file_a\\.md$", strict_order=1
                ),
                _make_deliverable(
                    action="read", pattern=".*file_b\\.md$", strict_order=1
                ),
            ]
        )
        # Both should be allowed since both are at level 1
        assert manager.get_strict_order_block_reason("read", "/path/file_a.md") is None
        assert manager.get_strict_order_block_reason("read", "/path/file_b.md") is None

    def test_no_strict_order_no_blocking(self, manager: StateManager):
        """When no deliverables have strict_order, nothing is blocked."""
        manager.set_deliverables(
            [
                _make_deliverable(
                    action="read", pattern=".*prompt\\.md$", strict_order=None
                ),
                _make_deliverable(
                    action="write", pattern=".*report\\.md$", strict_order=None
                ),
            ]
        )
        assert manager.get_strict_order_block_reason("read", "/path/prompt.md") is None
        assert manager.get_strict_order_block_reason("write", "/path/report.md") is None
        assert manager.get_strict_order_block_reason("bash", "npm test") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
