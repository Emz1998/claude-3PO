#!/usr/bin/env python3
"""Pytest tests for the task_dod_stop guard module."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from guards.task_dod_stop import TaskDodStopGuard  # type: ignore


@pytest.fixture
def guard():
    """Provide a guard instance with mocked state manager."""
    with patch("guards.task_dod_stop.get_manager") as mock_manager:
        mock_manager.return_value.is_workflow_active.return_value = True
        yield TaskDodStopGuard()


@pytest.fixture
def inactive_guard():
    """Provide a guard instance with inactive workflow."""
    with patch("guards.task_dod_stop.get_manager") as mock_manager:
        mock_manager.return_value.is_workflow_active.return_value = False
        yield TaskDodStopGuard()


class TestIsActive:
    """Tests for is_active method."""

    def test_active_when_workflow_active(self, guard):
        """Returns True when workflow is active."""
        assert guard.is_active() is True

    def test_inactive_when_workflow_inactive(self, inactive_guard):
        """Returns False when workflow is inactive."""
        assert inactive_guard.is_active() is False


class TestGetIncompleteTasks:
    """Tests for get_incomplete_tasks method."""

    @patch("release_plan.state.load_project_state")
    def test_returns_incomplete_task_ids(self, mock_state, guard):
        """Returns IDs of tasks not completed."""
        mock_state.return_value = {
            "current_tasks": {
                "T001": "completed",
                "T002": "in_progress",
                "T003": "not_started",
            }
        }
        result = guard.get_incomplete_tasks()
        assert "T002" in result
        assert "T003" in result
        assert "T001" not in result

    @patch("release_plan.state.load_project_state")
    def test_empty_when_all_completed(self, mock_state, guard):
        """Returns empty list when all tasks completed."""
        mock_state.return_value = {
            "current_tasks": {
                "T001": "completed",
                "T002": "completed",
            }
        }
        result = guard.get_incomplete_tasks()
        assert result == []

    @patch("release_plan.state.load_project_state")
    def test_empty_when_no_tasks(self, mock_state, guard):
        """Returns empty list when no current tasks."""
        mock_state.return_value = {"current_tasks": {}}
        result = guard.get_incomplete_tasks()
        assert result == []

    @patch("release_plan.state.load_project_state")
    def test_handles_missing_current_tasks(self, mock_state, guard):
        """Returns empty list when current_tasks key missing."""
        mock_state.return_value = {}
        result = guard.get_incomplete_tasks()
        assert result == []

    @patch("release_plan.state.load_project_state")
    def test_handles_none_state(self, mock_state, guard):
        """Returns empty list when state is None."""
        mock_state.return_value = None
        result = guard.get_incomplete_tasks()
        assert result == []

    @patch("release_plan.state.load_project_state")
    def test_includes_rt_prefixed_tasks(self, mock_state, guard):
        """RT-prefixed revision tasks are also checked."""
        mock_state.return_value = {
            "current_tasks": {
                "T001": "completed",
                "RT-1-001": "not_started",
            }
        }
        result = guard.get_incomplete_tasks()
        assert "RT-1-001" in result


class TestRun:
    """Tests for run method."""

    def test_inactive_workflow_exits_0(self, inactive_guard):
        """Inactive workflow exits with code 0."""
        with pytest.raises(SystemExit) as exc_info:
            inactive_guard.run({"hook_event_name": "Stop"})
        assert exc_info.value.code == 0

    @patch("release_plan.state.load_project_state")
    def test_all_completed_exits_0(self, mock_state, guard):
        """All tasks completed exits with code 0."""
        mock_state.return_value = {
            "current_tasks": {"T001": "completed", "T002": "completed"}
        }
        with pytest.raises(SystemExit) as exc_info:
            guard.run({"hook_event_name": "Stop"})
        assert exc_info.value.code == 0

    @patch("release_plan.state.load_project_state")
    def test_incomplete_tasks_exits_2(self, mock_state, guard):
        """Incomplete tasks exit with code 2 (block)."""
        mock_state.return_value = {
            "current_tasks": {"T001": "completed", "T002": "in_progress"}
        }
        with pytest.raises(SystemExit) as exc_info:
            guard.run({"hook_event_name": "Stop"})
        assert exc_info.value.code == 2

    @patch("release_plan.state.load_project_state")
    def test_block_message_includes_task_ids(self, mock_state, guard, capsys):
        """Block message includes incomplete task IDs."""
        mock_state.return_value = {
            "current_tasks": {"T001": "in_progress", "T002": "not_started"}
        }
        with pytest.raises(SystemExit):
            guard.run({"hook_event_name": "Stop"})

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["decision"] == "block"
        assert "T001" in output["reason"]
        assert "T002" in output["reason"]

    @patch("release_plan.state.load_project_state")
    def test_empty_tasks_exits_0(self, mock_state, guard):
        """No current tasks exits with code 0 (nothing to block)."""
        mock_state.return_value = {"current_tasks": {}}
        with pytest.raises(SystemExit) as exc_info:
            guard.run({"hook_event_name": "Stop"})
        assert exc_info.value.code == 0


class TestGuardImport:
    """Tests for guard imports."""

    def test_import_from_guards_package(self):
        """Can import TaskDodStopGuard from guards package."""
        from guards import TaskDodStopGuard
        assert TaskDodStopGuard is not None

    def test_import_from_module(self):
        """Can import directly from module."""
        from guards.task_dod_stop import TaskDodStopGuard, main
        assert TaskDodStopGuard is not None
        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
