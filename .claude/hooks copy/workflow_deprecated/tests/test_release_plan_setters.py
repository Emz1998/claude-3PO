#!/usr/bin/env python3
"""Pytest tests for the release_plan/new_setters module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from release_plan.new_setters import (  # type: ignore
    set_project_name,
    set_target_release,
    set_current_version,
    set_current_epic_id,
    set_current_feature_id,
    set_current_user_story,
    set_current_user_story_status,
    set_current_tasks,
    set_current_acs,
    set_current_scs,
    set_current_allowed_tasks,
    set_completed_tasks,
    set_completed_user_stories,
    set_completed_features,
    set_completed_epics,
    set_met_acs,
    set_met_scs,
    set_status,
    set_all_status_in_progress,
    set_all_status_completed,
    reset_all_tasks_status,
    reset_all_acs_status,
    reset_all_scs_status,
    reset_all_user_story_status,
)


@pytest.fixture
def mock_state():
    """Provide a complete mock state."""
    return {
        "name": "NEXLY RN",
        "target_release": "v1.0.0",
        "current_version": "v0.1.0",
        "current_epic": "EPIC-001",
        "current_feature": "FEAT-001",
        "current_user_story": "US-001",
        "current_user_story_status": "not_started",
        "current_tasks": {
            "T001": "not_started",
            "T002": "in_progress",
        },
        "current_acs": {
            "AC-001": "unmet",
            "AC-002": "unmet",
        },
        "current_scs": {
            "SC-001": "unmet",
            "SC-002": "unmet",
        },
        "current_allowed_tasks": ["T001", "T002"],
        "completed_tasks": [],
        "completed_user_stories": [],
        "completed_features": [],
        "completed_epics": [],
        "met_acs": [],
        "met_scs": [],
    }


class TestBasicPropertySetters:
    """Tests for basic property setters."""

    def test_set_project_name(self, mock_state):
        """Sets project name in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            set_project_name("New Project", mock_state)
            assert mock_state["name"] == "New Project"
            mock_save.assert_called_once_with(mock_state)

    def test_set_target_release(self, mock_state):
        """Sets target release in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            set_target_release("v2.0.0", mock_state)
            assert mock_state["target_release"] == "v2.0.0"
            mock_save.assert_called_once()

    def test_set_current_version(self, mock_state):
        """Sets current version in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            set_current_version("v0.2.0", mock_state)
            assert mock_state["current_version"] == "v0.2.0"
            mock_save.assert_called_once()

    def test_set_current_epic_id(self, mock_state):
        """Sets current epic ID in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            set_current_epic_id("EPIC-002", mock_state)
            assert mock_state["current_epic"] == "EPIC-002"
            mock_save.assert_called_once()

    def test_set_current_feature_id(self, mock_state):
        """Sets current feature ID in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            set_current_feature_id("FEAT-002", mock_state)
            assert mock_state["current_feature"] == "FEAT-002"
            mock_save.assert_called_once()

    def test_set_current_user_story(self, mock_state):
        """Sets current user story in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            set_current_user_story("US-002", mock_state)
            assert mock_state["current_user_story"] == "US-002"
            mock_save.assert_called_once()

    def test_set_current_user_story_status(self, mock_state):
        """Sets current user story status in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            set_current_user_story_status("in_progress", mock_state)
            assert mock_state["current_user_story_status"] == "in_progress"
            mock_save.assert_called_once()


class TestCollectionSetters:
    """Tests for collection setters."""

    def test_set_current_tasks(self, mock_state):
        """Sets current tasks dict in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            new_tasks = {"T003": "not_started", "T004": "not_started"}
            set_current_tasks(new_tasks, mock_state)
            assert mock_state["current_tasks"] == new_tasks
            mock_save.assert_called_once()

    def test_set_current_acs(self, mock_state):
        """Sets current ACs dict in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            new_acs = {"AC-003": "unmet"}
            set_current_acs(new_acs, mock_state)
            assert mock_state["current_acs"] == new_acs
            mock_save.assert_called_once()

    def test_set_current_scs(self, mock_state):
        """Sets current SCs dict in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            new_scs = {"SC-003": "unmet"}
            set_current_scs(new_scs, mock_state)
            assert mock_state["current_scs"] == new_scs
            mock_save.assert_called_once()

    def test_set_current_allowed_tasks(self, mock_state):
        """Sets current allowed tasks list in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            new_allowed = ["T003", "T004", "T005"]
            set_current_allowed_tasks(new_allowed, mock_state)
            assert mock_state["current_allowed_tasks"] == new_allowed
            mock_save.assert_called_once()


class TestCompletedItemsSetters:
    """Tests for completed items setters."""

    def test_set_completed_tasks(self, mock_state):
        """Sets completed tasks list in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            completed = ["T001", "T002"]
            set_completed_tasks(completed, mock_state)
            assert mock_state["completed_tasks"] == completed
            mock_save.assert_called_once()

    def test_set_completed_user_stories(self, mock_state):
        """Sets completed user stories list in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            completed = ["US-001"]
            set_completed_user_stories(completed, mock_state)
            assert mock_state["completed_user_stories"] == completed
            mock_save.assert_called_once()

    def test_set_completed_features(self, mock_state):
        """Sets completed features list in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            completed = ["FEAT-001"]
            set_completed_features(completed, mock_state)
            assert mock_state["completed_features"] == completed
            mock_save.assert_called_once()

    def test_set_completed_epics(self, mock_state):
        """Sets completed epics list in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            completed = ["EPIC-001"]
            set_completed_epics(completed, mock_state)
            assert mock_state["completed_epics"] == completed
            mock_save.assert_called_once()

    def test_set_met_acs(self, mock_state):
        """Sets met ACs list in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            met = ["AC-001", "AC-002"]
            set_met_acs(met, mock_state)
            assert mock_state["met_acs"] == met
            mock_save.assert_called_once()

    def test_set_met_scs(self, mock_state):
        """Sets met SCs list in state."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            met = ["SC-001", "SC-002"]
            set_met_scs(met, mock_state)
            assert mock_state["met_scs"] == met
            mock_save.assert_called_once()


class TestSetStatus:
    """Tests for set_status function."""

    def test_set_status_tasks_not_started_to_in_progress(self, mock_state):
        """Transitions tasks from not_started to in_progress."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            set_status("tasks", "in_progress", mock_state)
            assert mock_state["current_tasks"]["T001"] == "in_progress"
            # T002 was already in_progress, stays unchanged
            mock_save.assert_called_once()

    def test_set_status_tasks_in_progress_to_completed(self, mock_state):
        """Transitions tasks from in_progress to completed."""
        # First set T001 to in_progress so it can be completed
        mock_state["current_tasks"]["T001"] = "in_progress"
        with patch("release_plan.new_setters._save_state") as mock_save:
            set_status("tasks", "completed", mock_state)
            # Both tasks are now in_progress, both can go to completed
            assert mock_state["current_tasks"]["T001"] == "completed"
            assert mock_state["current_tasks"]["T002"] == "completed"
            mock_save.assert_called_once()

    def test_set_status_acs_unmet_to_met(self, mock_state):
        """Transitions ACs from unmet to met."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            set_status("acs", "met", mock_state)
            assert mock_state["current_acs"]["AC-001"] == "met"
            assert mock_state["current_acs"]["AC-002"] == "met"
            mock_save.assert_called_once()

    def test_set_status_scs_unmet_to_met(self, mock_state):
        """Transitions SCs from unmet to met."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            set_status("scs", "met", mock_state)
            assert mock_state["current_scs"]["SC-001"] == "met"
            mock_save.assert_called_once()


class TestBulkStatusSetters:
    """Tests for bulk status setters."""

    def test_set_all_status_in_progress(self, mock_state):
        """Sets all statuses to in_progress/unmet."""
        with patch("release_plan.new_setters._save_state") as mock_save, patch(
            "release_plan.new_setters.set_status"
        ) as mock_set:
            set_all_status_in_progress(mock_state)
            assert mock_set.call_count == 3
            mock_set.assert_any_call("tasks", "in_progress", mock_state)
            mock_set.assert_any_call("acs", "unmet", mock_state)
            mock_set.assert_any_call("scs", "unmet", mock_state)

    def test_set_all_status_completed(self, mock_state):
        """Sets all statuses to completed/met."""
        with patch("release_plan.new_setters._save_state") as mock_save, patch(
            "release_plan.new_setters.set_status"
        ) as mock_set:
            set_all_status_completed(mock_state)
            assert mock_set.call_count == 3
            mock_set.assert_any_call("tasks", "completed", mock_state)
            mock_set.assert_any_call("acs", "met", mock_state)
            mock_set.assert_any_call("scs", "met", mock_state)


class TestResetFunctions:
    """Tests for reset functions."""

    def test_reset_all_tasks_status(self, mock_state):
        """Resets all tasks to not_started."""
        with patch("release_plan.new_setters._save_state") as mock_save:
            reset_all_tasks_status(mock_state)
            assert mock_state["current_tasks"]["T001"] == "not_started"
            assert mock_state["current_tasks"]["T002"] == "not_started"
            mock_save.assert_called_once()

    def test_reset_all_acs_status(self, mock_state):
        """Resets all ACs to unmet."""
        mock_state["current_acs"]["AC-001"] = "met"
        with patch("release_plan.new_setters._save_state") as mock_save:
            reset_all_acs_status(mock_state)
            assert mock_state["current_acs"]["AC-001"] == "unmet"
            assert mock_state["current_acs"]["AC-002"] == "unmet"
            mock_save.assert_called_once()

    def test_reset_all_scs_status(self, mock_state):
        """Resets all SCs to unmet."""
        mock_state["current_scs"]["SC-001"] = "met"
        with patch("release_plan.new_setters._save_state") as mock_save:
            reset_all_scs_status(mock_state)
            assert mock_state["current_scs"]["SC-001"] == "unmet"
            mock_save.assert_called_once()

    def test_reset_all_user_story_status(self, mock_state):
        """Resets user story status to not_started."""
        mock_state["current_user_story_status"] = "in_progress"
        with patch("release_plan.new_setters._save_state") as mock_save:
            reset_all_user_story_status(mock_state)
            assert mock_state["current_user_story_status"] == "not_started"
            mock_save.assert_called_once()


class TestLoadStateWhenNoneProvided:
    """Tests for auto-loading state when None provided."""

    def test_setter_loads_state_when_none(self):
        """Setter loads state from file when None provided."""
        with patch("release_plan.new_setters._load_state") as mock_load, patch(
            "release_plan.new_setters._save_state"
        ) as mock_save:
            mock_load.return_value = {"name": ""}
            set_project_name("Test Project")
            mock_load.assert_called_once()


class TestImports:
    """Tests for module imports."""

    def test_all_setters_importable(self):
        """All setter functions can be imported."""
        from release_plan.new_setters import (
            set_project_name,
            set_target_release,
            set_current_version,
            set_current_epic_id,
            set_current_feature_id,
            set_current_user_story,
            set_current_tasks,
            set_current_acs,
            set_current_scs,
            set_completed_tasks,
            set_completed_user_stories,
            set_completed_features,
            set_completed_epics,
            set_met_acs,
            set_met_scs,
            set_status,
            reset_all_tasks_status,
            reset_all_acs_status,
            reset_all_scs_status,
        )

        assert all(
            callable(f)
            for f in [
                set_project_name,
                set_target_release,
                set_current_version,
                set_current_epic_id,
                set_current_feature_id,
                set_current_user_story,
                set_current_tasks,
                set_current_acs,
                set_current_scs,
                set_completed_tasks,
                set_completed_user_stories,
                set_completed_features,
                set_completed_epics,
                set_met_acs,
                set_met_scs,
                set_status,
                reset_all_tasks_status,
                reset_all_acs_status,
                reset_all_scs_status,
            ]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
