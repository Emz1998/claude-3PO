#!/usr/bin/env python3
"""Pytest tests for the release_plan_tracker module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from trackers.release_plan_tracker import ReleasePlanTracker  # type: ignore


@pytest.fixture
def tracker():
    """Provide a tracker instance with mocked state manager."""
    with patch("trackers.release_plan_tracker.get_manager") as mock_manager:
        mock_manager.return_value.is_workflow_active.return_value = True
        yield ReleasePlanTracker()


@pytest.fixture
def inactive_tracker():
    """Provide a tracker instance with inactive workflow."""
    with patch("trackers.release_plan_tracker.get_manager") as mock_manager:
        mock_manager.return_value.is_workflow_active.return_value = False
        yield ReleasePlanTracker()


class TestParseSkillArgs:
    """Tests for skill argument parsing."""

    def test_parse_empty_args(self, tracker):
        """Empty args returns empty strings."""
        item_id, status = tracker._parse_skill_args("")
        assert item_id == ""
        assert status == ""

    def test_parse_single_arg(self, tracker):
        """Single arg returns ID only."""
        item_id, status = tracker._parse_skill_args("T001")
        assert item_id == "T001"
        assert status == ""

    def test_parse_two_args(self, tracker):
        """Two args returns ID and status."""
        item_id, status = tracker._parse_skill_args("T001 completed")
        assert item_id == "T001"
        assert status == "completed"

    def test_parse_extra_args_ignored(self, tracker):
        """Extra args beyond two are ignored."""
        item_id, status = tracker._parse_skill_args("T001 completed extra")
        assert item_id == "T001"
        assert status == "completed"


class TestValidateLogTask:
    """Tests for log:task validation."""

    def test_missing_args(self, tracker):
        """Missing args returns error."""
        is_valid, error = tracker.validate_log_task("")
        assert not is_valid
        assert "Missing log:task arguments" in error

    def test_missing_status(self, tracker):
        """Missing status returns error."""
        is_valid, error = tracker.validate_log_task("T001")
        assert not is_valid
        assert "Missing status" in error

    def test_invalid_status(self, tracker):
        """Invalid status returns error."""
        is_valid, error = tracker.validate_log_task("T001 invalid")
        assert not is_valid
        assert "Invalid status" in error

    @patch("trackers.release_plan_tracker.find_task")
    def test_task_not_found(self, mock_find, tracker):
        """Task not in release plan returns error."""
        mock_find.return_value = None
        is_valid, error = tracker.validate_log_task("T999 completed")
        assert not is_valid
        assert "not found in release plan" in error

    @patch("trackers.release_plan_tracker.find_task")
    def test_valid_task(self, mock_find, tracker):
        """Valid task and status passes."""
        mock_find.return_value = {"id": "T001", "description": "Test task"}
        is_valid, error = tracker.validate_log_task("T001 completed")
        assert is_valid
        assert error == ""

    @patch("trackers.release_plan_tracker.find_task")
    def test_all_valid_statuses(self, mock_find, tracker):
        """All valid task statuses pass."""
        mock_find.return_value = {"id": "T001"}
        for status in ["not_started", "in_progress", "completed", "blocked"]:
            is_valid, _ = tracker.validate_log_task(f"T001 {status}")
            assert is_valid, f"Status '{status}' should be valid"


class TestValidateLogAC:
    """Tests for log:ac validation."""

    def test_missing_args(self, tracker):
        """Missing args returns error."""
        is_valid, error = tracker.validate_log_ac("")
        assert not is_valid
        assert "Missing log:ac arguments" in error

    def test_missing_status(self, tracker):
        """Missing status returns error."""
        is_valid, error = tracker.validate_log_ac("AC-001")
        assert not is_valid
        assert "Missing status" in error

    def test_invalid_status(self, tracker):
        """Invalid status returns error."""
        is_valid, error = tracker.validate_log_ac("AC-001 invalid")
        assert not is_valid
        assert "Invalid status" in error

    @patch("trackers.release_plan_tracker.find_acceptance_criteria")
    def test_ac_not_found(self, mock_find, tracker):
        """AC not in release plan returns error."""
        mock_find.return_value = None
        is_valid, error = tracker.validate_log_ac("AC-999 met")
        assert not is_valid
        assert "not found in release plan" in error

    @patch("trackers.release_plan_tracker.find_acceptance_criteria")
    def test_valid_ac(self, mock_find, tracker):
        """Valid AC and status passes."""
        mock_find.return_value = {"id": "AC-001", "description": "Test AC"}
        is_valid, error = tracker.validate_log_ac("AC-001 met")
        assert is_valid
        assert error == ""

    @patch("trackers.release_plan_tracker.find_acceptance_criteria")
    def test_all_valid_statuses(self, mock_find, tracker):
        """All valid AC statuses pass."""
        mock_find.return_value = {"id": "AC-001"}
        for status in ["met", "unmet"]:
            is_valid, _ = tracker.validate_log_ac(f"AC-001 {status}")
            assert is_valid, f"Status '{status}' should be valid"


class TestValidateLogSC:
    """Tests for log:sc validation."""

    def test_missing_args(self, tracker):
        """Missing args returns error."""
        is_valid, error = tracker.validate_log_sc("")
        assert not is_valid
        assert "Missing log:sc arguments" in error

    def test_missing_status(self, tracker):
        """Missing status returns error."""
        is_valid, error = tracker.validate_log_sc("SC-001")
        assert not is_valid
        assert "Missing status" in error

    def test_invalid_status(self, tracker):
        """Invalid status returns error."""
        is_valid, error = tracker.validate_log_sc("SC-001 invalid")
        assert not is_valid
        assert "Invalid status" in error

    @patch("trackers.release_plan_tracker.find_success_criteria")
    def test_sc_not_found(self, mock_find, tracker):
        """SC not in release plan returns error."""
        mock_find.return_value = None
        is_valid, error = tracker.validate_log_sc("SC-999 met")
        assert not is_valid
        assert "not found in release plan" in error

    @patch("trackers.release_plan_tracker.find_success_criteria")
    def test_valid_sc(self, mock_find, tracker):
        """Valid SC and status passes."""
        mock_find.return_value = {"id": "SC-001", "description": "Test SC"}
        is_valid, error = tracker.validate_log_sc("SC-001 met")
        assert is_valid
        assert error == ""

    @patch("trackers.release_plan_tracker.find_success_criteria")
    def test_all_valid_statuses(self, mock_find, tracker):
        """All valid SC statuses pass."""
        mock_find.return_value = {"id": "SC-001"}
        for status in ["met", "unmet"]:
            is_valid, _ = tracker.validate_log_sc(f"SC-001 {status}")
            assert is_valid, f"Status '{status}' should be valid"


class TestRunPreTool:
    """Tests for pre-tool validation phase."""

    def test_inactive_workflow_skips(self, inactive_tracker):
        """Inactive workflow does not validate."""
        hook_input = {
            "tool_name": "Skill",
            "tool_input": {"skill": "log:task", "args": "invalid"},
        }
        # Should not raise or exit
        inactive_tracker.run_pre_tool(hook_input)

    def test_non_skill_tool_skips(self, tracker):
        """Non-Skill tools are skipped."""
        hook_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/path"},
        }
        tracker.run_pre_tool(hook_input)

    def test_non_log_skill_skips(self, tracker):
        """Non-log skills are skipped."""
        hook_input = {
            "tool_name": "Skill",
            "tool_input": {"skill": "commit", "args": ""},
        }
        tracker.run_pre_tool(hook_input)

    @patch("trackers.release_plan_tracker.find_task")
    def test_valid_log_task_passes(self, mock_find, tracker):
        """Valid log:task passes pre-tool check."""
        mock_find.return_value = {"id": "T001"}
        hook_input = {
            "tool_name": "Skill",
            "tool_input": {"skill": "log:task", "args": "T001 completed"},
        }
        tracker.run_pre_tool(hook_input)

    @patch("trackers.release_plan_tracker.find_task")
    def test_invalid_log_task_exits(self, mock_find, tracker):
        """Invalid log:task exits with code 2."""
        mock_find.return_value = None
        hook_input = {
            "tool_name": "Skill",
            "tool_input": {"skill": "log:task", "args": "T999 completed"},
        }
        with pytest.raises(SystemExit) as exc_info:
            tracker.run_pre_tool(hook_input)
        assert exc_info.value.code == 2


class TestRunPostTool:
    """Tests for post-tool recording phase."""

    def test_inactive_workflow_skips(self, inactive_tracker):
        """Inactive workflow does not record."""
        hook_input = {
            "tool_name": "Skill",
            "tool_input": {"skill": "log:task", "args": "T001 completed"},
        }
        inactive_tracker.run_post_tool(hook_input)

    def test_non_skill_tool_skips(self, tracker):
        """Non-Skill tools are skipped."""
        hook_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/path"},
        }
        tracker.run_post_tool(hook_input)

    @patch("trackers.release_plan_tracker.record_completed_task")
    def test_log_task_completed_records(self, mock_record, tracker):
        """log:task with completed status records task."""
        hook_input = {
            "tool_name": "Skill",
            "tool_input": {"skill": "log:task", "args": "T001 completed"},
        }
        tracker.run_post_tool(hook_input)
        mock_record.assert_called_once_with("T001")

    @patch("trackers.release_plan_tracker.record_completed_task")
    def test_log_task_in_progress_not_recorded(self, mock_record, tracker):
        """log:task with in_progress status does not record."""
        hook_input = {
            "tool_name": "Skill",
            "tool_input": {"skill": "log:task", "args": "T001 in_progress"},
        }
        tracker.run_post_tool(hook_input)
        mock_record.assert_not_called()

    @patch("trackers.release_plan_tracker.record_met_ac")
    def test_log_ac_met_records(self, mock_record, tracker):
        """log:ac with met status records AC."""
        hook_input = {
            "tool_name": "Skill",
            "tool_input": {"skill": "log:ac", "args": "AC-001 met"},
        }
        tracker.run_post_tool(hook_input)
        mock_record.assert_called_once_with("AC-001")

    @patch("trackers.release_plan_tracker.record_met_ac")
    def test_log_ac_unmet_not_recorded(self, mock_record, tracker):
        """log:ac with unmet status does not record."""
        hook_input = {
            "tool_name": "Skill",
            "tool_input": {"skill": "log:ac", "args": "AC-001 unmet"},
        }
        tracker.run_post_tool(hook_input)
        mock_record.assert_not_called()

    @patch("trackers.release_plan_tracker.record_met_sc")
    def test_log_sc_met_records(self, mock_record, tracker):
        """log:sc with met status records SC."""
        hook_input = {
            "tool_name": "Skill",
            "tool_input": {"skill": "log:sc", "args": "SC-001 met"},
        }
        tracker.run_post_tool(hook_input)
        mock_record.assert_called_once_with("SC-001")

    @patch("trackers.release_plan_tracker.record_met_sc")
    def test_log_sc_unmet_not_recorded(self, mock_record, tracker):
        """log:sc with unmet status does not record."""
        hook_input = {
            "tool_name": "Skill",
            "tool_input": {"skill": "log:sc", "args": "SC-001 unmet"},
        }
        tracker.run_post_tool(hook_input)
        mock_record.assert_not_called()


class TestRunBackwardsCompatible:
    """Tests for backwards compatible run() method."""

    @patch("trackers.release_plan_tracker.find_task")
    def test_run_with_pre_tool_use(self, mock_find, tracker):
        """run() with PreToolUse calls run_pre_tool."""
        mock_find.return_value = {"id": "T001"}
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "log:task", "args": "T001 completed"},
        }
        tracker.run(hook_input)
        mock_find.assert_called_once()

    @patch("trackers.release_plan_tracker.record_completed_task")
    def test_run_with_post_tool_use(self, mock_record, tracker):
        """run() with PostToolUse calls run_post_tool."""
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "log:task", "args": "T001 completed"},
        }
        tracker.run(hook_input)
        mock_record.assert_called_once()


class TestImports:
    """Tests for module imports."""

    def test_tracker_import(self):
        """ReleasePlanTracker can be imported."""
        from trackers.release_plan_tracker import ReleasePlanTracker

        assert ReleasePlanTracker is not None

    def test_function_import(self):
        """track_release_plan function can be imported."""
        from trackers.release_plan_tracker import track_release_plan

        assert callable(track_release_plan)

    def test_from_init(self):
        """Can import from trackers __init__."""
        from trackers import ReleasePlanTracker, track_release_plan

        assert ReleasePlanTracker is not None
        assert callable(track_release_plan)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
