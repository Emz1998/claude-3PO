#!/usr/bin/env python3
"""Pytest tests for validation integration across modified modules.

Tests the changes to:
- StateManager pending_validation methods
- ReleasePlanTracker RT- support and validation checks
- ContextInjector validation context injection
- Checkers task-only/story-only completion functions
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.state_manager import StateManager  # type: ignore


@pytest.fixture
def state_manager():
    """Provide a fresh state manager for each test."""
    manager = StateManager()
    manager.reset()
    yield manager
    manager.reset()


class TestStateManagerPendingValidation:
    """Tests for pending_validation methods on StateManager."""

    def test_get_pending_validation_default_none(self, state_manager):
        """Default pending_validation is None."""
        assert state_manager.get_pending_validation() is None

    def test_set_pending_validation_ac(self, state_manager):
        """Can set pending_validation to 'ac'."""
        state_manager.set_pending_validation("ac")
        assert state_manager.get_pending_validation() == "ac"

    def test_set_pending_validation_sc(self, state_manager):
        """Can set pending_validation to 'sc'."""
        state_manager.set_pending_validation("sc")
        assert state_manager.get_pending_validation() == "sc"

    def test_set_pending_validation_epic_sc(self, state_manager):
        """Can set pending_validation to 'epic_sc'."""
        state_manager.set_pending_validation("epic_sc")
        assert state_manager.get_pending_validation() == "epic_sc"

    def test_clear_pending_validation(self, state_manager):
        """clear_pending_validation removes the flag."""
        state_manager.set_pending_validation("ac")
        state_manager.clear_pending_validation()
        assert state_manager.get_pending_validation() is None

    def test_clear_when_not_set(self, state_manager):
        """Clearing when not set does not raise."""
        state_manager.clear_pending_validation()
        assert state_manager.get_pending_validation() is None

    def test_overwrite_pending_validation(self, state_manager):
        """Setting again overwrites previous value."""
        state_manager.set_pending_validation("ac")
        state_manager.set_pending_validation("sc")
        assert state_manager.get_pending_validation() == "sc"


class TestReleasePlanTrackerRevisionTasks:
    """Tests for RT- prefixed task support in ReleasePlanTracker."""

    @pytest.fixture
    def tracker(self):
        """Provide a tracker instance with mocked state manager."""
        with patch("trackers.release_plan_tracker.get_manager") as mock_manager:
            mock_manager.return_value.is_workflow_active.return_value = True
            from trackers.release_plan_tracker import ReleasePlanTracker  # type: ignore

            yield ReleasePlanTracker()

    def test_is_revision_task_id_true(self, tracker):
        """RT- prefixed IDs are recognized as revision tasks."""
        assert tracker._is_revision_task_id("RT-1-001") is True
        assert tracker._is_revision_task_id("RT-3-015") is True

    def test_is_revision_task_id_false(self, tracker):
        """Non-RT IDs are not revision tasks."""
        assert tracker._is_revision_task_id("T001") is False
        assert tracker._is_revision_task_id("AC-001") is False
        assert tracker._is_revision_task_id("") is False

    @patch("release_plan.state.load_project_state")
    def test_validate_rt_task_found(self, mock_state, tracker):
        """RT task in current_tasks validates successfully."""
        mock_state.return_value = {"current_tasks": {"RT-1-001": "not_started"}}
        is_valid, error = tracker.validate_log_task("RT-1-001 completed")
        assert is_valid
        assert error == ""

    @patch("release_plan.state.load_project_state")
    def test_validate_rt_task_not_found(self, mock_state, tracker):
        """RT task not in current_tasks returns error."""
        mock_state.return_value = {"current_tasks": {}}
        is_valid, error = tracker.validate_log_task("RT-1-001 completed")
        assert not is_valid
        assert "not found in current tasks" in error

    @patch("release_plan.state.load_project_state")
    def test_validate_rt_task_invalid_status(self, mock_state, tracker):
        """RT task with invalid status returns error."""
        is_valid, error = tracker.validate_log_task("RT-1-001 invalid")
        assert not is_valid
        assert "Invalid status" in error


class TestReleasePlanTrackerValidationChecks:
    """Tests for _check_*_validation_needed methods."""

    @pytest.fixture
    def tracker(self):
        """Provide a tracker with mocked state manager."""
        with patch("trackers.release_plan_tracker.get_manager") as mock_manager:
            self.mock_state = MagicMock()
            mock_manager.return_value = self.mock_state
            self.mock_state.is_workflow_active.return_value = True
            from trackers.release_plan_tracker import ReleasePlanTracker  # type: ignore

            yield ReleasePlanTracker()

    @patch("trackers.release_plan_tracker.load_release_plan")
    @patch("trackers.release_plan_tracker.get_all_acs_ids_in_user_story")
    @patch("trackers.release_plan_tracker.are_all_tasks_completed_in_user_story")
    @patch("trackers.release_plan_tracker.get_current_user_story")
    @patch("release_plan.state.load_project_state")
    def test_check_ac_sets_flag_when_needed(
        self, mock_proj_state, mock_us, mock_tasks, mock_acs, mock_plan, tracker
    ):
        """Sets needs_ac_validation when tasks done and ACs unmet."""
        mock_proj_state.return_value = {}
        mock_us.return_value = "US-001"
        mock_tasks.return_value = True
        mock_plan.return_value = {}
        mock_acs.return_value = ["AC-001"]

        with patch("trackers.release_plan_tracker.is_ac_met", return_value=False):
            tracker._check_ac_validation_needed()

        self.mock_state.set.assert_called_with("needs_ac_validation", True)

    @patch("trackers.release_plan_tracker.are_all_tasks_completed_in_user_story")
    @patch("trackers.release_plan_tracker.get_current_user_story")
    @patch("release_plan.state.load_project_state")
    def test_check_ac_no_flag_when_tasks_incomplete(
        self, mock_proj_state, mock_us, mock_tasks, tracker
    ):
        """Does not set flag when tasks are incomplete."""
        mock_proj_state.return_value = {}
        mock_us.return_value = "US-001"
        mock_tasks.return_value = False

        tracker._check_ac_validation_needed()
        self.mock_state.set.assert_not_called()

    @patch("trackers.release_plan_tracker.get_current_user_story")
    @patch("release_plan.state.load_project_state")
    def test_check_ac_no_flag_when_no_us(self, mock_proj_state, mock_us, tracker):
        """Does not set flag when no current user story."""
        mock_proj_state.return_value = {}
        mock_us.return_value = None

        tracker._check_ac_validation_needed()
        self.mock_state.set.assert_not_called()

    @patch("trackers.release_plan_tracker.load_release_plan")
    @patch("trackers.release_plan_tracker.get_all_scs_ids_in_feature")
    @patch("trackers.release_plan_tracker.are_all_user_stories_completed_in_feature")
    @patch("trackers.release_plan_tracker.get_current_feature_id")
    @patch("release_plan.state.load_project_state")
    def test_check_sc_sets_flag_when_needed(
        self, mock_proj_state, mock_feat, mock_stories, mock_scs, mock_plan, tracker
    ):
        """Sets needs_sc_validation when stories done and SCs unmet."""
        mock_proj_state.return_value = {}
        mock_feat.return_value = "FEAT-001"
        mock_stories.return_value = True
        mock_plan.return_value = {}
        mock_scs.return_value = ["SC-001"]

        with patch("trackers.release_plan_tracker.is_sc_met", return_value=False):
            tracker._check_sc_validation_needed()

        self.mock_state.set.assert_called_with("needs_sc_validation", True)

    @patch("trackers.release_plan_tracker.load_release_plan")
    @patch("trackers.release_plan_tracker.find_epic")
    @patch("trackers.release_plan_tracker.are_all_features_completed_in_epic")
    @patch("trackers.release_plan_tracker.get_current_epic_id")
    @patch("release_plan.state.load_project_state")
    def test_check_epic_sc_sets_flag_when_needed(
        self, mock_proj_state, mock_epic, mock_feats, mock_find, mock_plan, tracker
    ):
        """Sets needs_epic_sc_validation when features done and epic SCs unmet."""
        mock_proj_state.return_value = {"met_epic_scs": []}
        mock_epic.return_value = "EPIC-001"
        mock_feats.return_value = True
        mock_plan.return_value = {}
        mock_find.return_value = {"success_criteria": [{"id": "ESC-001"}]}

        tracker._check_epic_sc_validation_needed()
        self.mock_state.set.assert_called_with("needs_epic_sc_validation", True)


class TestReleasePlanTrackerPostToolValidation:
    """Tests for post-tool validation chain triggering."""

    @pytest.fixture
    def tracker(self):
        """Provide a tracker with validation check methods mocked."""
        with patch("trackers.release_plan_tracker.get_manager") as mock_manager:
            mock_manager.return_value.is_workflow_active.return_value = True
            from trackers.release_plan_tracker import ReleasePlanTracker  # type: ignore

            t = ReleasePlanTracker()
            yield t

    @patch("trackers.release_plan_tracker.record_completed_task")
    def test_task_completed_triggers_ac_check(self, mock_record, tracker):
        """Completing a task triggers AC validation check."""
        with patch.object(tracker, "_check_ac_validation_needed") as mock_check:
            hook_input = {
                "tool_name": "Skill",
                "tool_input": {"skill": "log:task", "args": "T001 completed"},
            }
            tracker.run_post_tool(hook_input)
            mock_check.assert_called_once()

    @patch("trackers.release_plan_tracker.record_met_ac")
    def test_ac_met_triggers_sc_check(self, mock_record, tracker):
        """Meeting an AC triggers SC validation check."""
        with patch.object(tracker, "_check_sc_validation_needed") as mock_check:
            hook_input = {
                "tool_name": "Skill",
                "tool_input": {"skill": "log:ac", "args": "AC-001 met"},
            }
            tracker.run_post_tool(hook_input)
            mock_check.assert_called_once()

    @patch("trackers.release_plan_tracker.record_met_sc")
    def test_sc_met_triggers_epic_check(self, mock_record, tracker):
        """Meeting an SC triggers epic SC validation check."""
        with patch.object(tracker, "_check_epic_sc_validation_needed") as mock_check:
            hook_input = {
                "tool_name": "Skill",
                "tool_input": {"skill": "log:sc", "args": "SC-001 met"},
            }
            tracker.run_post_tool(hook_input)
            mock_check.assert_called_once()


class TestContextInjectorValidation:
    """Tests for ContextInjector validation context injection."""

    @pytest.fixture
    def injector(self):
        """Provide injector with mocked state."""
        with patch("context.context_injector.get_manager") as mock_manager:
            self.mock_state = MagicMock()
            mock_manager.return_value = self.mock_state
            self.mock_state.is_workflow_active.return_value = True
            from context.context_injector import ContextInjector  # type: ignore

            yield ContextInjector()

    @patch("context.context_injector.add_context")
    def test_no_validation_returns_false(self, mock_add, injector):
        """Returns False when no pending validation."""
        self.mock_state.get_pending_validation.return_value = None
        assert injector.inject_validation_context() is False
        mock_add.assert_not_called()

    @patch("context.context_injector.add_context")
    @patch("validators.criteria_validator.get_unmet_acs")
    def test_ac_validation_injects_context(self, mock_unmet, mock_add, injector):
        """Injects AC validation context when pending."""
        self.mock_state.get_pending_validation.return_value = "ac"
        mock_unmet.return_value = ["AC-001", "AC-002"]

        result = injector.inject_validation_context()
        assert result is True
        mock_add.assert_called_once()
        context_arg = mock_add.call_args[0][0]
        assert "VALIDATION REQUIRED" in context_arg
        assert "AC-001" in context_arg
        assert "Acceptance Criteria" in context_arg

    @patch("context.context_injector.add_context")
    @patch("validators.criteria_validator.get_unmet_scs")
    def test_sc_validation_injects_context(self, mock_unmet, mock_add, injector):
        """Injects SC validation context when pending."""
        self.mock_state.get_pending_validation.return_value = "sc"
        mock_unmet.return_value = ["SC-001"]

        result = injector.inject_validation_context()
        assert result is True
        context_arg = mock_add.call_args[0][0]
        assert "Success Criteria" in context_arg

    @patch("context.context_injector.add_context")
    @patch("validators.criteria_validator.get_unmet_epic_scs")
    def test_epic_sc_validation_injects_context(self, mock_unmet, mock_add, injector):
        """Injects epic SC validation context when pending."""
        self.mock_state.get_pending_validation.return_value = "epic_sc"
        mock_unmet.return_value = ["ESC-001"]

        result = injector.inject_validation_context()
        assert result is True
        context_arg = mock_add.call_args[0][0]
        assert "Epic Success Criteria" in context_arg

    def test_run_checks_validation_before_phase(self, injector):
        """run() checks validation context before normal phase injection."""
        self.mock_state.get_pending_validation.return_value = "ac"

        with patch.object(injector, "inject_validation_context", return_value=True):
            with patch.object(injector, "inject") as mock_inject:
                injector.run(
                    {
                        "hook_event_name": "PostToolUse",
                        "tool_name": "Skill",
                        "tool_input": {"skill": "plan"},
                    }
                )
                mock_inject.assert_not_called()


class TestCheckersTaskOnlyCompletion:
    """Tests for task-only/story-only checkers."""

    @patch("release_plan.checkers.load_release_plan")
    @patch("release_plan.checkers.get_all_tasks_ids_in_user_story")
    def test_all_tasks_completed_in_us(self, mock_ids, mock_plan):
        """Returns True when all tasks in US are completed."""
        from release_plan.checkers import are_all_tasks_completed_in_user_story

        mock_plan.return_value = {}
        mock_ids.return_value = ["T001", "T002"]

        state = {"current_tasks": {"T001": "completed", "T002": "completed"}}
        with patch(
            "release_plan.checkers.is_task_completed", side_effect=lambda t, s: True
        ):
            assert are_all_tasks_completed_in_user_story("US-001", state) is True

    @patch("release_plan.checkers.load_release_plan")
    @patch("release_plan.checkers.get_all_tasks_ids_in_user_story")
    def test_not_all_tasks_completed_in_us(self, mock_ids, mock_plan):
        """Returns False when some tasks are incomplete."""
        from release_plan.checkers import are_all_tasks_completed_in_user_story

        mock_plan.return_value = {}
        mock_ids.return_value = ["T001", "T002"]

        with patch(
            "release_plan.checkers.is_task_completed",
            side_effect=lambda t, s: t == "T001",
        ):
            assert are_all_tasks_completed_in_user_story("US-001", {}) is False

    @patch("release_plan.checkers.load_release_plan")
    @patch("release_plan.checkers.get_all_tasks_ids_in_user_story")
    def test_no_tasks_returns_false(self, mock_ids, mock_plan):
        """Returns False when user story has no tasks."""
        from release_plan.checkers import are_all_tasks_completed_in_user_story

        mock_plan.return_value = {}
        mock_ids.return_value = []

        assert are_all_tasks_completed_in_user_story("US-001", {}) is False

    @patch("release_plan.checkers.load_release_plan")
    @patch("release_plan.checkers.get_all_user_story_ids_in_feature")
    def test_all_stories_completed_in_feature(self, mock_ids, mock_plan):
        """Returns True when all user stories in feature are completed."""
        from release_plan.checkers import are_all_user_stories_completed_in_feature

        mock_plan.return_value = {}
        mock_ids.return_value = ["US-001", "US-002"]

        state = {"completed_user_stories": ["US-001", "US-002"]}
        assert are_all_user_stories_completed_in_feature("FEAT-001", state) is True

    @patch("release_plan.checkers.load_release_plan")
    @patch("release_plan.checkers.get_all_user_story_ids_in_feature")
    def test_not_all_stories_completed(self, mock_ids, mock_plan):
        """Returns False when some stories are incomplete."""
        from release_plan.checkers import are_all_user_stories_completed_in_feature

        mock_plan.return_value = {}
        mock_ids.return_value = ["US-001", "US-002"]

        state = {"completed_user_stories": ["US-001"]}
        assert are_all_user_stories_completed_in_feature("FEAT-001", state) is False

    @patch("release_plan.checkers.load_release_plan")
    @patch("release_plan.checkers.get_all_features_ids_in_epic")
    def test_all_features_completed_in_epic(self, mock_ids, mock_plan):
        """Returns True when all features in epic are completed."""
        from release_plan.checkers import are_all_features_completed_in_epic

        mock_plan.return_value = {}
        mock_ids.return_value = ["FEAT-001", "FEAT-002"]

        state = {"completed_features": ["FEAT-001", "FEAT-002"]}
        assert are_all_features_completed_in_epic("EPIC-001", state) is True

    @patch("release_plan.checkers.load_release_plan")
    @patch("release_plan.checkers.get_all_features_ids_in_epic")
    def test_not_all_features_completed(self, mock_ids, mock_plan):
        """Returns False when some features are incomplete."""
        from release_plan.checkers import are_all_features_completed_in_epic

        mock_plan.return_value = {}
        mock_ids.return_value = ["FEAT-001", "FEAT-002"]

        state = {"completed_features": ["FEAT-001"]}
        assert are_all_features_completed_in_epic("EPIC-001", state) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
