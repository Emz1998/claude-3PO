#!/usr/bin/env python3
"""Pytest tests for the phase_tracker module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from trackers.phase_tracker import PhaseTracker, track_phase  # type: ignore


@pytest.fixture
def tracker():
    """Provide a tracker instance with mocked dependencies."""
    with patch("trackers.phase_tracker.get_manager") as mock_manager, patch(
        "trackers.phase_tracker.get_tracker"
    ) as mock_deliverables:
        mock_manager.return_value.is_workflow_active.return_value = True
        mock_manager.return_value.set_current_phase = MagicMock()
        mock_deliverables.return_value.initialize_for_phase = MagicMock()
        yield PhaseTracker()


@pytest.fixture
def inactive_tracker():
    """Provide a tracker instance with inactive workflow."""
    with patch("trackers.phase_tracker.get_manager") as mock_manager, patch(
        "trackers.phase_tracker.get_tracker"
    ) as mock_deliverables:
        mock_manager.return_value.is_workflow_active.return_value = False
        yield PhaseTracker()


class TestIsActive:
    """Tests for is_active method."""

    def test_active_when_workflow_active(self, tracker):
        """Returns True when workflow is active."""
        assert tracker.is_active() is True

    def test_inactive_when_workflow_inactive(self, inactive_tracker):
        """Returns False when workflow is inactive."""
        assert inactive_tracker.is_active() is False


class TestTrack:
    """Tests for track method."""

    def test_track_updates_state_and_initializes_deliverables(self):
        """Verify track() calls state manager and deliverables tracker."""
        with patch("trackers.phase_tracker.get_manager") as mock_manager, patch(
            "trackers.phase_tracker.get_tracker"
        ) as mock_deliverables, patch(
            "core.workflow_auditor.get_auditor"
        ) as mock_auditor:
            mock_state = MagicMock()
            mock_state.is_workflow_active.return_value = True
            mock_state.get_deliverables.return_value = []
            mock_manager.return_value = mock_state

            mock_del_tracker = MagicMock()
            mock_deliverables.return_value = mock_del_tracker

            mock_auditor_instance = MagicMock()
            mock_auditor.return_value = mock_auditor_instance

            tracker = PhaseTracker()
            tracker.track("explore")

            mock_state.set_current_phase.assert_called_once_with("explore")
            mock_del_tracker.initialize_for_phase.assert_called_once_with("explore")


class TestRun:
    """Tests for run method."""

    def test_run_handles_skill_tool_post_use(self):
        """Verify run() processes Skill tool correctly."""
        with patch("trackers.phase_tracker.get_manager") as mock_manager, patch(
            "trackers.phase_tracker.get_tracker"
        ) as mock_deliverables, patch(
            "trackers.phase_tracker.normalize_skill_name"
        ) as mock_normalize, patch(
            "core.workflow_auditor.get_auditor"
        ) as mock_auditor:
            mock_state = MagicMock()
            mock_state.is_workflow_active.return_value = True
            mock_state.get_deliverables.return_value = []
            mock_manager.return_value = mock_state

            mock_auditor.return_value = MagicMock()

            mock_normalize.return_value = "explore"

            tracker = PhaseTracker()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "explore"},
            }
            tracker.run(hook_input)

            mock_state.set_current_phase.assert_called_once_with("explore")

    def test_run_normalizes_workflow_prefix(self):
        """Verify workflow:explore → explore normalization."""
        with patch("trackers.phase_tracker.get_manager") as mock_manager, patch(
            "trackers.phase_tracker.get_tracker"
        ) as mock_deliverables, patch(
            "trackers.phase_tracker.normalize_skill_name"
        ) as mock_normalize, patch(
            "core.workflow_auditor.get_auditor"
        ) as mock_auditor:
            mock_state = MagicMock()
            mock_state.is_workflow_active.return_value = True
            mock_state.get_deliverables.return_value = []
            mock_manager.return_value = mock_state

            mock_auditor.return_value = MagicMock()

            mock_normalize.return_value = "explore"

            tracker = PhaseTracker()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "workflow:explore"},
            }
            tracker.run(hook_input)

            mock_normalize.assert_called_with("workflow:explore")

    def test_run_exits_early_when_inactive(self, inactive_tracker):
        """Verify exits with 0 when workflow inactive."""
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "explore"},
        }
        with pytest.raises(SystemExit) as exc_info:
            inactive_tracker.run(hook_input)
        assert exc_info.value.code == 0

    def test_run_ignores_non_post_tool_use_events(self, tracker):
        """Verify ignores other events."""
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "explore"},
        }
        # Should return without doing anything
        tracker.run(hook_input)

    def test_run_ignores_non_skill_tools(self, tracker):
        """Verify ignores Read/Write/etc tools."""
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/file.txt"},
        }
        # Should return without doing anything
        tracker.run(hook_input)

    def test_run_ignores_empty_skill_name(self, tracker):
        """Verify ignores empty skill name."""
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": ""},
        }
        # Should return without doing anything
        tracker.run(hook_input)


class TestTrackPhaseFunction:
    """Tests for track_phase convenience function."""

    def test_track_phase_creates_tracker_and_calls_track(self):
        """Verify track_phase function works correctly."""
        with patch("trackers.phase_tracker.get_manager") as mock_manager, patch(
            "trackers.phase_tracker.get_tracker"
        ) as mock_deliverables, patch(
            "core.workflow_auditor.get_auditor"
        ) as mock_auditor:
            mock_state = MagicMock()
            mock_state.is_workflow_active.return_value = True
            mock_state.get_deliverables.return_value = []
            mock_manager.return_value = mock_state

            mock_auditor.return_value = MagicMock()

            track_phase("plan")

            mock_state.set_current_phase.assert_called_once_with("plan")


class TestImports:
    """Tests for module imports."""

    def test_tracker_import(self):
        """PhaseTracker can be imported."""
        from trackers.phase_tracker import PhaseTracker

        assert PhaseTracker is not None

    def test_function_import(self):
        """track_phase function can be imported."""
        from trackers.phase_tracker import track_phase

        assert callable(track_phase)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
