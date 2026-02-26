#!/usr/bin/env python3
"""Pytest tests for the release_plan/getters module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from release_plan.getters import (  # type: ignore
    get_project_name,
    get_target_release,
    get_current_version,
    get_current_epic_id,
    get_current_feature_id,
    get_current_user_story,
    get_current_tasks,
    get_current_tasks_ids,
    get_current_task_dependencies,
    get_current_acs,
    get_current_acs_ids,
    get_current_scs,
    get_current_scs_ids,
    get_current_allowed_tasks,
    get_completed_tasks,
    get_completed_user_stories,
    get_completed_features,
    get_completed_epics,
    get_met_acs,
    get_met_scs,
    get_tasks_with_completed_deps,
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
        "current_tasks": {
            "T001": "not_started",
            "T002": "in_progress",
            "T003": "completed",
        },
        "current_acs": {
            "AC-001": "unmet",
            "AC-002": "met",
        },
        "current_scs": {
            "SC-001": "unmet",
            "SC-002": "met",
        },
        "current_allowed_tasks": ["T001", "T002"],
        "completed_tasks": ["T003", "T004"],
        "completed_user_stories": ["US-000"],
        "completed_features": [],
        "completed_epics": [],
        "met_acs": ["AC-002"],
        "met_scs": ["SC-002"],
    }


class TestProjectPropertyGetters:
    """Tests for basic project property getters."""

    def test_get_project_name(self, mock_state):
        """Returns project name from state."""
        result = get_project_name(mock_state)
        assert result == "NEXLY RN"

    def test_get_project_name_with_none_state(self):
        """Returns empty string when state is None."""
        with patch("release_plan.getters._load_state") as mock_load:
            mock_load.return_value = None
            result = get_project_name()
            assert result == ""

    def test_get_target_release(self, mock_state):
        """Returns target release from state."""
        result = get_target_release(mock_state)
        assert result == "v1.0.0"

    def test_get_current_version(self, mock_state):
        """Returns current version from state."""
        result = get_current_version(mock_state)
        assert result == "v0.1.0"

    def test_get_current_epic_id(self, mock_state):
        """Returns current epic ID from state."""
        result = get_current_epic_id(mock_state)
        assert result == "EPIC-001"

    def test_get_current_feature_id(self, mock_state):
        """Returns current feature ID from state."""
        result = get_current_feature_id(mock_state)
        assert result == "FEAT-001"

    def test_get_current_user_story(self, mock_state):
        """Returns current user story from state."""
        result = get_current_user_story(mock_state)
        assert result == "US-001"


class TestTasksGetters:
    """Tests for task-related getters."""

    def test_get_current_tasks(self, mock_state):
        """Returns current tasks dict from state."""
        result = get_current_tasks(mock_state)
        assert result == {
            "T001": "not_started",
            "T002": "in_progress",
            "T003": "completed",
        }

    def test_get_current_tasks_ids(self, mock_state):
        """Returns list of current task IDs."""
        result = get_current_tasks_ids(mock_state)
        assert set(result) == {"T001", "T002", "T003"}

    def test_get_current_tasks_ids_with_empty_tasks(self):
        """Returns empty list when no tasks."""
        state = {"current_tasks": {}}
        result = get_current_tasks_ids(state)
        assert result == []

    def test_get_current_tasks_ids_with_none_tasks(self):
        """Returns empty list when current_tasks is None."""
        state = {"current_tasks": None}
        result = get_current_tasks_ids(state)
        assert result == []

    def test_get_current_task_dependencies(self, mock_state):
        """Returns task dependencies."""
        with patch("release_plan.getters.load_release_plan") as mock_load, patch(
            "release_plan.getters.get_task_dependencies_ids"
        ) as mock_deps:
            mock_load.return_value = {"tasks": {}}
            mock_deps.return_value = ["T001", "T002"]

            result = get_current_task_dependencies("T003", mock_state)
            assert result == ["T001", "T002"]

    def test_get_current_allowed_tasks(self, mock_state):
        """Returns current allowed tasks list."""
        result = get_current_allowed_tasks(mock_state)
        assert result == ["T001", "T002"]


class TestAcceptanceCriteriaGetters:
    """Tests for AC-related getters."""

    def test_get_current_acs(self, mock_state):
        """Returns current ACs dict from state."""
        result = get_current_acs(mock_state)
        assert result == {"AC-001": "unmet", "AC-002": "met"}

    def test_get_current_acs_ids(self, mock_state):
        """Returns list of current AC IDs."""
        result = get_current_acs_ids(mock_state)
        assert set(result) == {"AC-001", "AC-002"}


class TestSuccessCriteriaGetters:
    """Tests for SC-related getters."""

    def test_get_current_scs(self, mock_state):
        """Returns current SCs dict from state."""
        result = get_current_scs(mock_state)
        assert result == {"SC-001": "unmet", "SC-002": "met"}

    def test_get_current_scs_ids(self, mock_state):
        """Returns list of current SC IDs."""
        result = get_current_scs_ids(mock_state)
        assert set(result) == {"SC-001", "SC-002"}


class TestCompletedItemsGetters:
    """Tests for completed items getters."""

    def test_get_completed_tasks(self, mock_state):
        """Returns completed tasks list."""
        result = get_completed_tasks(mock_state)
        assert result == ["T003", "T004"]

    def test_get_completed_user_stories(self, mock_state):
        """Returns completed user stories list."""
        result = get_completed_user_stories(mock_state)
        assert result == ["US-000"]

    def test_get_completed_features(self, mock_state):
        """Returns completed features list."""
        result = get_completed_features(mock_state)
        assert result == []

    def test_get_completed_epics(self, mock_state):
        """Returns completed epics list."""
        result = get_completed_epics(mock_state)
        assert result == []

    def test_get_met_acs(self, mock_state):
        """Returns met ACs list."""
        result = get_met_acs(mock_state)
        assert result == ["AC-002"]

    def test_get_met_scs(self, mock_state):
        """Returns met SCs list."""
        result = get_met_scs(mock_state)
        assert result == ["SC-002"]


class TestTasksWithCompletedDeps:
    """Tests for get_tasks_with_completed_deps."""

    def test_get_tasks_with_completed_deps(self, mock_state):
        """Returns tasks with completed dependencies."""
        with patch("release_plan.getters.load_release_plan") as mock_load, patch(
            "release_plan.checkers.are_task_deps_completed"
        ) as mock_check:
            mock_load.return_value = {"tasks": {}}
            mock_check.side_effect = lambda task_id, rp, state: task_id in [
                "T001",
                "T002",
            ]

            result = get_tasks_with_completed_deps(
                "T001", "T002", "T003", state=mock_state
            )
            assert "T001" in result
            assert "T002" in result
            assert "T003" not in result

    def test_get_tasks_with_completed_deps_empty(self, mock_state):
        """Returns empty list when no tasks provided."""
        with patch("release_plan.getters.load_release_plan") as mock_load:
            mock_load.return_value = {}
            result = get_tasks_with_completed_deps(state=mock_state)
            assert result == []


class TestMissingKeys:
    """Tests for handling missing keys in state."""

    def test_get_current_tasks_missing_key(self):
        """Returns empty dict when key missing."""
        result = get_current_tasks({})
        assert result == {}

    def test_get_completed_tasks_missing_key(self):
        """Returns empty list when key missing."""
        result = get_completed_tasks({})
        assert result == []

    def test_get_current_allowed_tasks_missing_key(self):
        """Returns empty list when key missing."""
        result = get_current_allowed_tasks({})
        assert result == []


class TestImports:
    """Tests for module imports."""

    def test_all_getters_importable(self):
        """All getter functions can be imported."""
        from release_plan.getters import (
            get_project_name,
            get_target_release,
            get_current_version,
            get_current_epic_id,
            get_current_feature_id,
            get_current_user_story,
            get_current_tasks,
            get_current_tasks_ids,
            get_current_acs,
            get_current_acs_ids,
            get_current_scs,
            get_current_scs_ids,
            get_current_allowed_tasks,
            get_completed_tasks,
            get_completed_user_stories,
            get_completed_features,
            get_completed_epics,
            get_met_acs,
            get_met_scs,
        )

        assert all(
            callable(f)
            for f in [
                get_project_name,
                get_target_release,
                get_current_version,
                get_current_epic_id,
                get_current_feature_id,
                get_current_user_story,
                get_current_tasks,
                get_current_tasks_ids,
                get_current_acs,
                get_current_acs_ids,
                get_current_scs,
                get_current_scs_ids,
                get_current_allowed_tasks,
                get_completed_tasks,
                get_completed_user_stories,
                get_completed_features,
                get_completed_epics,
                get_met_acs,
                get_met_scs,
            ]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
