#!/usr/bin/env python3
"""Pytest tests for the release_plan/resolvers module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from release_plan.resolvers import (  # type: ignore
    initialize_tasks,
    initialize_acs,
    initialize_scs,
    refresh_current_tasks,
    record_completed_task,
    record_completed_user_story,
    record_completed_feature,
    record_completed_epic,
    record_met_ac,
    record_met_sc,
    resolve_tasks,
    resolve_completed_acs,
    resolve_completed_scs,
    resolve_user_story,
    resolve_feature,
    resolve_epic,
    resolve_state,
    increment_id,
)


@pytest.fixture
def mock_state():
    """Provide a complete mock state."""
    return {
        "current_epic": "EPIC-001",
        "current_feature": "FEAT-001",
        "current_user_story": "US-001",
        "current_tasks": {
            "T001": "not_started",
            "T002": "completed",
        },
        "current_acs": {
            "AC-001": "unmet",
            "AC-002": "met",
        },
        "current_scs": {
            "SC-001": "met",
        },
        "completed_tasks": ["T000"],
        "completed_user_stories": [],
        "completed_features": [],
        "completed_epics": [],
        "met_acs": ["AC-002"],
        "met_scs": ["SC-001"],
    }


class TestInitializers:
    """Tests for initializer functions."""

    def test_initialize_tasks_returns_dict(self, mock_state):
        """Initializes tasks for user story returns dict with not_started status."""
        # Just verify it returns a dict (implementation details depend on release plan data)
        result = initialize_tasks("US-001", {}, mock_state)
        assert isinstance(result, dict)

    def test_initialize_tasks_returns_not_started_status(self, mock_state):
        """All initialized tasks have not_started status."""
        with patch("release_plan.resolvers._load_state") as mock_load:
            mock_load.return_value = mock_state
            result = initialize_tasks("US-001", {}, mock_state)
            # All values should be "not_started"
            for status in result.values():
                assert status == "not_started"

    def test_initialize_acs_returns_unmet_status(self):
        """All initialized ACs have unmet status."""
        result = initialize_acs("US-001", {})
        # All values should be "unmet"
        for status in result.values():
            assert status == "unmet"

    def test_initialize_scs_returns_unmet_status(self):
        """All initialized SCs have unmet status."""
        result = initialize_scs("FEAT-001", {})
        # All values should be "unmet"
        for status in result.values():
            assert status == "unmet"


class TestRefreshCurrentTasks:
    """Tests for refresh_current_tasks function."""

    def test_refresh_current_tasks(self, mock_state):
        """Refreshes current tasks with allowed tasks."""
        with patch("release_plan.resolvers._load_state") as mock_load, patch(
            "release_plan.resolvers._save_state"
        ) as mock_save, patch(
            "release_plan.resolvers.load_release_plan"
        ) as mock_rp, patch(
            "release_plan.resolvers.get_all_tasks_ids_in_user_story"
        ) as mock_get, patch(
            "release_plan.resolvers.is_task_completed"
        ) as mock_completed, patch(
            "release_plan.resolvers.is_task_allowed"
        ) as mock_allowed:
            mock_load.return_value = mock_state
            mock_rp.return_value = {}
            mock_get.return_value = ["T001", "T002", "T003"]
            mock_completed.side_effect = lambda t, s: t == "T002"
            mock_allowed.side_effect = lambda t, s: t in ["T001", "T003"]

            result = refresh_current_tasks(mock_state)

            assert "T001" in result
            assert "T003" in result
            assert "T002" not in result  # completed


class TestRecordCompleted:
    """Tests for record_completed_* functions."""

    def test_record_completed_task(self, mock_state):
        """Records completed task."""
        with patch("release_plan.resolvers._load_state") as mock_load, patch(
            "release_plan.resolvers.is_task_completed"
        ) as mock_check, patch(
            "release_plan.resolvers.set_completed_tasks"
        ) as mock_set, patch(
            "release_plan.resolvers.refresh_current_tasks"
        ):
            mock_load.return_value = mock_state
            mock_check.return_value = True

            result = record_completed_task("T002", mock_state)

            assert result is True
            mock_set.assert_called_once()

    def test_record_completed_task_not_completed(self, mock_state):
        """Returns False when task not completed."""
        with patch("release_plan.resolvers.is_task_completed") as mock_check:
            mock_check.return_value = False

            result = record_completed_task("T001", mock_state)

            assert result is False

    def test_record_completed_task_already_recorded(self, mock_state):
        """Returns False when task already in completed list."""
        mock_state["completed_tasks"] = ["T002"]
        with patch("release_plan.resolvers.is_task_completed") as mock_check:
            mock_check.return_value = True

            result = record_completed_task("T002", mock_state)

            assert result is False

    def test_record_completed_user_story(self, mock_state):
        """Records completed user story."""
        with patch(
            "release_plan.resolvers.is_user_story_completed"
        ) as mock_check, patch(
            "release_plan.resolvers.set_completed_user_stories"
        ) as mock_set:
            mock_check.return_value = True

            result = record_completed_user_story("US-001", mock_state)

            assert result is True
            mock_set.assert_called_once()

    def test_record_completed_feature(self, mock_state):
        """Records completed feature."""
        with patch("release_plan.resolvers.is_feature_completed") as mock_check, patch(
            "release_plan.resolvers.set_completed_features"
        ) as mock_set:
            mock_check.return_value = True

            result = record_completed_feature("FEAT-001", mock_state)

            assert result is True
            mock_set.assert_called_once()

    def test_record_completed_epic(self, mock_state):
        """Records completed epic."""
        with patch("release_plan.resolvers.is_epic_completed") as mock_check, patch(
            "release_plan.resolvers.set_completed_epics"
        ) as mock_set:
            mock_check.return_value = True

            result = record_completed_epic("EPIC-001", mock_state)

            assert result is True
            mock_set.assert_called_once()

    def test_record_met_ac(self, mock_state):
        """Records met AC."""
        with patch("release_plan.resolvers.is_ac_met") as mock_check, patch(
            "release_plan.resolvers.set_met_acs"
        ) as mock_set:
            mock_check.return_value = True

            result = record_met_ac("AC-001", mock_state)

            assert result is True
            mock_set.assert_called_once()

    def test_record_met_sc(self, mock_state):
        """Records met SC."""
        with patch("release_plan.resolvers.is_sc_met") as mock_check, patch(
            "release_plan.resolvers.set_met_scs"
        ) as mock_set:
            mock_check.return_value = True
            mock_state["met_scs"] = []  # Reset so it can be recorded

            result = record_met_sc("SC-001", mock_state)

            assert result is True
            mock_set.assert_called_once()


class TestBatchResolvers:
    """Tests for batch resolver functions."""

    def test_resolve_tasks(self, mock_state):
        """Resolves all completed tasks."""
        with patch("release_plan.resolvers.get_current_tasks_ids") as mock_get, patch(
            "release_plan.resolvers.record_completed_task"
        ) as mock_record:
            mock_get.return_value = ["T001", "T002"]

            result = resolve_tasks(mock_state)

            assert result is True
            assert mock_record.call_count == 2

    def test_resolve_completed_acs(self, mock_state):
        """Resolves all met ACs."""
        with patch("release_plan.resolvers.get_current_acs_ids") as mock_get, patch(
            "release_plan.resolvers.record_met_ac"
        ) as mock_record:
            mock_get.return_value = ["AC-001", "AC-002"]

            result = resolve_completed_acs(mock_state)

            assert result is True
            assert mock_record.call_count == 2

    def test_resolve_completed_scs(self, mock_state):
        """Resolves all met SCs."""
        with patch("release_plan.resolvers.get_current_scs_ids") as mock_get, patch(
            "release_plan.resolvers.record_met_sc"
        ) as mock_record:
            mock_get.return_value = ["SC-001"]

            result = resolve_completed_scs(mock_state)

            assert result is True
            mock_record.assert_called_once()


class TestComplexResolvers:
    """Tests for complex resolver functions."""

    def test_resolve_user_story_moves_to_next(self, mock_state):
        """Resolves user story and moves to next."""
        with patch("release_plan.resolvers._load_state") as mock_load, patch(
            "release_plan.resolvers.resolve_tasks"
        ), patch("release_plan.resolvers.resolve_completed_acs"), patch(
            "release_plan.resolvers.resolve_completed_scs"
        ), patch(
            "release_plan.resolvers.is_user_story_completed"
        ) as mock_check, patch(
            "release_plan.resolvers.record_completed_user_story"
        ), patch(
            "release_plan.resolvers.load_release_plan"
        ) as mock_rp, patch(
            "release_plan.resolvers.get_next_user_story_id_in_feature"
        ) as mock_next, patch(
            "release_plan.resolvers.set_current_user_story"
        ), patch(
            "release_plan.resolvers.initialize_tasks"
        ) as mock_init_tasks, patch(
            "release_plan.resolvers.initialize_acs"
        ) as mock_init_acs, patch(
            "release_plan.resolvers.set_current_tasks"
        ), patch(
            "release_plan.resolvers.set_current_acs"
        ):
            mock_load.return_value = mock_state
            mock_check.return_value = True
            mock_rp.return_value = {}
            mock_next.return_value = "US-002"
            mock_init_tasks.return_value = {}
            mock_init_acs.return_value = {}

            result = resolve_user_story(mock_state)

            assert result is True

    def test_resolve_user_story_not_completed(self, mock_state):
        """Returns False when user story not completed."""
        with patch("release_plan.resolvers._load_state") as mock_load, patch(
            "release_plan.resolvers.resolve_tasks"
        ), patch("release_plan.resolvers.resolve_completed_acs"), patch(
            "release_plan.resolvers.resolve_completed_scs"
        ), patch(
            "release_plan.resolvers.is_user_story_completed"
        ) as mock_check:
            mock_load.return_value = mock_state
            mock_check.return_value = False

            result = resolve_user_story(mock_state)

            assert result is False


class TestIncrementId:
    """Tests for increment_id utility function."""

    def test_increment_id_basic(self):
        """Increments ID correctly."""
        assert increment_id("US-001") == "US-002"
        assert increment_id("US-009") == "US-010"
        assert increment_id("T001") == "T002"

    def test_increment_id_three_digits(self):
        """Handles three-digit IDs."""
        assert increment_id("AC-999") == "AC-1000"  # Increments to 1000
        assert increment_id("SC-123") == "SC-124"


class TestImports:
    """Tests for module imports."""

    def test_all_functions_importable(self):
        """All resolver functions can be imported."""
        from release_plan.resolvers import (
            initialize_tasks,
            initialize_acs,
            initialize_scs,
            refresh_current_tasks,
            record_completed_task,
            record_completed_user_story,
            record_completed_feature,
            record_completed_epic,
            record_met_ac,
            record_met_sc,
            resolve_tasks,
            resolve_completed_acs,
            resolve_completed_scs,
            resolve_user_story,
            resolve_feature,
            resolve_epic,
            resolve_state,
            increment_id,
        )

        assert all(
            callable(f)
            for f in [
                initialize_tasks,
                initialize_acs,
                initialize_scs,
                refresh_current_tasks,
                record_completed_task,
                record_completed_user_story,
                record_completed_feature,
                record_completed_epic,
                record_met_ac,
                record_met_sc,
                resolve_tasks,
                resolve_completed_acs,
                resolve_completed_scs,
                resolve_user_story,
                resolve_feature,
                resolve_epic,
                resolve_state,
                increment_id,
            ]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
