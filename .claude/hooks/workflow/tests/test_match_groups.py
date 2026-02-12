#!/usr/bin/env python3
"""Pytest tests for match group OR-deliverable completion."""

import sys
from pathlib import Path

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
    action: str = "edit",
    pattern: str = ".*\\.ts$",
    match: str | None = None,
    completed: bool = False,
) -> dict:
    return {
        "type": "files",
        "action": action,
        "pattern": pattern,
        "match": match,
        "completed": completed,
    }


# =========================================================================
# match group cascade tests
# =========================================================================


class TestMatchGroupCompletesAll:
    """Completing one entry marks all in the same (action, match) group."""

    def test_completing_one_marks_all_in_group(self, manager: StateManager):
        manager.set_deliverables([
            _make_deliverable(action="edit", pattern=".*\\.test\\.ts$", match="test-files"),
            _make_deliverable(action="edit", pattern=".*\\.test\\.tsx$", match="test-files"),
            _make_deliverable(action="edit", pattern=".*\\.py$", match="test-files"),
        ])
        result = manager.mark_deliverable_complete("edit", "src/foo.test.ts")
        assert result is True
        deliverables = manager.get_deliverables()
        assert all(d["completed"] for d in deliverables)

    def test_completing_second_entry_marks_all(self, manager: StateManager):
        manager.set_deliverables([
            _make_deliverable(action="edit", pattern=".*\\.test\\.ts$", match="test-files"),
            _make_deliverable(action="edit", pattern=".*\\.test\\.tsx$", match="test-files"),
        ])
        result = manager.mark_deliverable_complete("edit", "src/Button.test.tsx")
        assert result is True
        deliverables = manager.get_deliverables()
        assert all(d["completed"] for d in deliverables)


class TestMatchGroupScopedByAction:
    """Same match name under different actions are independent groups."""

    def test_different_actions_independent(self, manager: StateManager):
        manager.set_deliverables([
            _make_deliverable(action="read", pattern=".*\\.md$", match="docs"),
            _make_deliverable(action="write", pattern=".*\\.md$", match="docs"),
        ])
        manager.mark_deliverable_complete("read", "readme.md")
        deliverables = manager.get_deliverables()
        read_entry = [d for d in deliverables if d["action"] == "read"][0]
        write_entry = [d for d in deliverables if d["action"] == "write"][0]
        assert read_entry["completed"] is True
        assert write_entry["completed"] is False


class TestNoMatchIndividuallyRequired:
    """Entries without match stay AND'd (individually required)."""

    def test_no_match_entries_independent(self, manager: StateManager):
        manager.set_deliverables([
            _make_deliverable(action="edit", pattern=".*\\.ts$", match=None),
            _make_deliverable(action="edit", pattern=".*\\.tsx$", match=None),
        ])
        manager.mark_deliverable_complete("edit", "src/foo.ts")
        deliverables = manager.get_deliverables()
        ts_entry = [d for d in deliverables if d["pattern"] == ".*\\.ts$"][0]
        tsx_entry = [d for d in deliverables if d["pattern"] == ".*\\.tsx$"][0]
        assert ts_entry["completed"] is True
        assert tsx_entry["completed"] is False


class TestMixedMatchAndNoMatch:
    """Group entries and standalone entries coexist correctly."""

    def test_mixed_coexistence(self, manager: StateManager):
        manager.set_deliverables([
            _make_deliverable(action="edit", pattern=".*\\.ts$", match="source"),
            _make_deliverable(action="edit", pattern=".*\\.tsx$", match="source"),
            _make_deliverable(action="edit", pattern=".*\\.css$", match=None),
        ])
        manager.mark_deliverable_complete("edit", "src/app.ts")
        deliverables = manager.get_deliverables()
        ts_entry = [d for d in deliverables if d["pattern"] == ".*\\.ts$"][0]
        tsx_entry = [d for d in deliverables if d["pattern"] == ".*\\.tsx$"][0]
        css_entry = [d for d in deliverables if d["pattern"] == ".*\\.css$"][0]
        assert ts_entry["completed"] is True
        assert tsx_entry["completed"] is True
        assert css_entry["completed"] is False


class TestDifferentMatchNamesIndependent:
    """Two different match groups under the same action are AND'd."""

    def test_different_groups_independent(self, manager: StateManager):
        manager.set_deliverables([
            _make_deliverable(action="edit", pattern=".*\\.test\\.ts$", match="tests"),
            _make_deliverable(action="edit", pattern=".*\\.test\\.tsx$", match="tests"),
            _make_deliverable(action="edit", pattern=".*\\.ts$", match="source"),
            _make_deliverable(action="edit", pattern=".*\\.tsx$", match="source"),
        ])
        manager.mark_deliverable_complete("edit", "src/foo.test.ts")
        deliverables = manager.get_deliverables()
        tests_group = [d for d in deliverables if d["match"] == "tests"]
        source_group = [d for d in deliverables if d["match"] == "source"]
        assert all(d["completed"] for d in tests_group)
        assert not any(d["completed"] for d in source_group)


class TestAreAllMetWithMatchGroups:
    """Phase passes when one per group is done plus all standalone entries."""

    def test_passes_with_one_per_group(self, manager: StateManager):
        manager.set_deliverables([
            _make_deliverable(action="edit", pattern=".*\\.ts$", match="source"),
            _make_deliverable(action="edit", pattern=".*\\.tsx$", match="source"),
            _make_deliverable(action="write", pattern=".*report\\.md$", match=None),
        ])
        manager.mark_deliverable_complete("edit", "src/index.ts")
        manager.mark_deliverable_complete("write", "reports/report.md")
        all_met, msg = manager.are_all_deliverables_met()
        assert all_met is True

    def test_fails_when_group_incomplete(self, manager: StateManager):
        manager.set_deliverables([
            _make_deliverable(action="edit", pattern=".*\\.ts$", match="source"),
            _make_deliverable(action="edit", pattern=".*\\.tsx$", match="source"),
            _make_deliverable(action="write", pattern=".*report\\.md$", match=None),
        ])
        manager.mark_deliverable_complete("write", "reports/report.md")
        all_met, msg = manager.are_all_deliverables_met()
        assert all_met is False

    def test_fails_when_standalone_incomplete(self, manager: StateManager):
        manager.set_deliverables([
            _make_deliverable(action="edit", pattern=".*\\.ts$", match="source"),
            _make_deliverable(action="edit", pattern=".*\\.tsx$", match="source"),
            _make_deliverable(action="write", pattern=".*report\\.md$", match=None),
        ])
        manager.mark_deliverable_complete("edit", "src/index.ts")
        all_met, msg = manager.are_all_deliverables_met()
        assert all_met is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
