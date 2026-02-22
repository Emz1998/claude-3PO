#!/usr/bin/env python3
"""Pytest tests for the trackers/deliverables_tracker module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from trackers.deliverables_tracker import DeliverableTracker, track_deliverable  # type: ignore


@pytest.fixture
def tracker():
    """Provide a tracker instance with mocked dependencies."""
    with patch("trackers.deliverables_tracker.get_manager") as mock_manager, patch(
        "trackers.deliverables_tracker.get_deliverables_tracker"
    ) as mock_deliverables:
        mock_manager.return_value.is_workflow_active.return_value = True
        mock_deliverables.return_value.mark_complete = MagicMock(return_value=True)
        yield DeliverableTracker()


@pytest.fixture
def inactive_tracker():
    """Provide a tracker instance with inactive workflow."""
    with patch("trackers.deliverables_tracker.get_manager") as mock_manager, patch(
        "trackers.deliverables_tracker.get_deliverables_tracker"
    ) as mock_deliverables:
        mock_manager.return_value.is_workflow_active.return_value = False
        yield DeliverableTracker()


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

    def test_track_marks_deliverable_complete(self):
        """Verify track() calls deliverables tracker."""
        with patch("trackers.deliverables_tracker.get_manager") as mock_manager, patch(
            "trackers.deliverables_tracker.get_deliverables_tracker"
        ) as mock_deliverables:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_del_tracker = MagicMock()
            mock_del_tracker.mark_complete.return_value = True
            mock_deliverables.return_value = mock_del_tracker

            tracker = DeliverableTracker()
            result = tracker.track("write", "/path/to/file.ts")

            mock_del_tracker.mark_complete.assert_called_once_with(
                "write", "/path/to/file.ts"
            )
            assert result is True


class TestRun:
    """Tests for run method."""

    def test_run_marks_file_deliverable_complete_write(self):
        """Verify Write tool tracking."""
        with patch("trackers.deliverables_tracker.get_manager") as mock_manager, patch(
            "trackers.deliverables_tracker.get_deliverables_tracker"
        ) as mock_deliverables:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_del_tracker = MagicMock()
            mock_deliverables.return_value = mock_del_tracker

            tracker = DeliverableTracker()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": "/src/components/Button.tsx"},
            }
            tracker.run(hook_input)

            mock_del_tracker.mark_complete.assert_called_once_with(
                "write", "/src/components/Button.tsx"
            )

    def test_run_marks_file_deliverable_complete_read(self):
        """Verify Read tool tracking."""
        with patch("trackers.deliverables_tracker.get_manager") as mock_manager, patch(
            "trackers.deliverables_tracker.get_deliverables_tracker"
        ) as mock_deliverables:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_del_tracker = MagicMock()
            mock_deliverables.return_value = mock_del_tracker

            tracker = DeliverableTracker()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "/src/config/settings.ts"},
            }
            tracker.run(hook_input)

            mock_del_tracker.mark_complete.assert_called_once_with(
                "read", "/src/config/settings.ts"
            )

    def test_run_marks_file_deliverable_complete_edit(self):
        """Verify Edit tool tracking."""
        with patch("trackers.deliverables_tracker.get_manager") as mock_manager, patch(
            "trackers.deliverables_tracker.get_deliverables_tracker"
        ) as mock_deliverables:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_del_tracker = MagicMock()
            mock_deliverables.return_value = mock_del_tracker

            tracker = DeliverableTracker()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": "/src/utils/helpers.ts"},
            }
            tracker.run(hook_input)

            mock_del_tracker.mark_complete.assert_called_once_with(
                "edit", "/src/utils/helpers.ts"
            )

    def test_run_marks_bash_deliverable_complete(self):
        """Verify Bash command tracking."""
        with patch("trackers.deliverables_tracker.get_manager") as mock_manager, patch(
            "trackers.deliverables_tracker.get_deliverables_tracker"
        ) as mock_deliverables:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_del_tracker = MagicMock()
            mock_deliverables.return_value = mock_del_tracker

            tracker = DeliverableTracker()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "npm test"},
            }
            tracker.run(hook_input)

            mock_del_tracker.mark_complete.assert_called_once_with("bash", "npm test")

    def test_run_marks_skill_deliverable_complete(self):
        """Verify Skill invocation tracking."""
        with patch("trackers.deliverables_tracker.get_manager") as mock_manager, patch(
            "trackers.deliverables_tracker.get_deliverables_tracker"
        ) as mock_deliverables:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_del_tracker = MagicMock()
            mock_deliverables.return_value = mock_del_tracker

            tracker = DeliverableTracker()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "commit"},
            }
            tracker.run(hook_input)

            mock_del_tracker.mark_complete.assert_called_once_with("invoke", "commit")

    def test_run_exits_early_when_inactive(self, inactive_tracker):
        """Verify exits when workflow inactive."""
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "/some/file.ts"},
        }
        with pytest.raises(SystemExit) as exc_info:
            inactive_tracker.run(hook_input)
        assert exc_info.value.code == 0

    def test_run_ignores_non_post_tool_use_events(self, tracker):
        """Verify ignores other events."""
        with patch("trackers.deliverables_tracker.get_manager") as mock_manager, patch(
            "trackers.deliverables_tracker.get_deliverables_tracker"
        ) as mock_deliverables:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_del_tracker = MagicMock()
            mock_deliverables.return_value = mock_del_tracker

            tracker = DeliverableTracker()
            hook_input = {
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": "/some/file.ts"},
            }
            tracker.run(hook_input)

            mock_del_tracker.mark_complete.assert_not_called()

    def test_run_ignores_unsupported_tools(self, tracker):
        """Verify ignores unsupported tools like Task."""
        with patch("trackers.deliverables_tracker.get_manager") as mock_manager, patch(
            "trackers.deliverables_tracker.get_deliverables_tracker"
        ) as mock_deliverables:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_del_tracker = MagicMock()
            mock_deliverables.return_value = mock_del_tracker

            tracker = DeliverableTracker()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Task",
                "tool_input": {"subagent_type": "Explore"},
            }
            tracker.run(hook_input)

            mock_del_tracker.mark_complete.assert_not_called()

    def test_run_ignores_empty_file_path(self):
        """Verify ignores empty file path."""
        with patch("trackers.deliverables_tracker.get_manager") as mock_manager, patch(
            "trackers.deliverables_tracker.get_deliverables_tracker"
        ) as mock_deliverables:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_del_tracker = MagicMock()
            mock_deliverables.return_value = mock_del_tracker

            tracker = DeliverableTracker()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": ""},
            }
            tracker.run(hook_input)

            mock_del_tracker.mark_complete.assert_not_called()


class TestTrackDeliverableFunction:
    """Tests for track_deliverable convenience function."""

    def test_track_deliverable_works(self):
        """Verify track_deliverable function works correctly."""
        with patch("trackers.deliverables_tracker.get_manager") as mock_manager, patch(
            "trackers.deliverables_tracker.get_deliverables_tracker"
        ) as mock_deliverables:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_del_tracker = MagicMock()
            mock_del_tracker.mark_complete.return_value = True
            mock_deliverables.return_value = mock_del_tracker

            result = track_deliverable("write", "/path/to/file.ts")

            mock_del_tracker.mark_complete.assert_called_once_with(
                "write", "/path/to/file.ts"
            )
            assert result is True


class TestImports:
    """Tests for module imports."""

    def test_tracker_import(self):
        """DeliverableTracker can be imported."""
        from trackers.deliverables_tracker import DeliverableTracker

        assert DeliverableTracker is not None

    def test_function_import(self):
        """track_deliverable function can be imported."""
        from trackers.deliverables_tracker import track_deliverable

        assert callable(track_deliverable)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
