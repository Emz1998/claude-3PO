#!/usr/bin/env python3
"""Pytest tests for the criteria_validator module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from validators.criteria_validator import (  # type: ignore
    get_unmet_acs,
    get_unmet_scs,
    get_unmet_epic_scs,
    has_pending_ac_validation,
    has_pending_sc_validation,
    has_pending_epic_sc_validation,
    get_pending_validation_type,
)


VALIDATOR_MODULE = "validators.criteria_validator"


class TestGetUnmetAcs:
    """Tests for get_unmet_acs function."""

    @patch(f"{VALIDATOR_MODULE}.load_release_plan")
    @patch(f"{VALIDATOR_MODULE}.get_all_acs_ids_in_user_story")
    @patch(f"{VALIDATOR_MODULE}.get_current_user_story")
    @patch(f"{VALIDATOR_MODULE}.is_ac_met")
    def test_returns_unmet_acs(self, mock_met, mock_us, mock_ids, mock_plan):
        """Returns AC IDs that are not met."""
        mock_us.return_value = "US-001"
        mock_plan.return_value = {}
        mock_ids.return_value = ["AC-001", "AC-002", "AC-003"]
        mock_met.side_effect = lambda ac_id, state: ac_id == "AC-001"

        state = {"current_user_story": "US-001"}
        result = get_unmet_acs(state)
        assert result == ["AC-002", "AC-003"]

    @patch(f"{VALIDATOR_MODULE}.load_release_plan")
    @patch(f"{VALIDATOR_MODULE}.get_all_acs_ids_in_user_story")
    @patch(f"{VALIDATOR_MODULE}.get_current_user_story")
    @patch(f"{VALIDATOR_MODULE}.is_ac_met")
    def test_all_met_returns_empty(self, mock_met, mock_us, mock_ids, mock_plan):
        """Returns empty list when all ACs are met."""
        mock_us.return_value = "US-001"
        mock_plan.return_value = {}
        mock_ids.return_value = ["AC-001", "AC-002"]
        mock_met.return_value = True

        result = get_unmet_acs({})
        assert result == []

    @patch(f"{VALIDATOR_MODULE}.load_release_plan")
    @patch(f"{VALIDATOR_MODULE}.get_all_acs_ids_in_user_story")
    @patch(f"{VALIDATOR_MODULE}.get_current_user_story")
    def test_no_acs_returns_empty(self, mock_us, mock_ids, mock_plan):
        """Returns empty list when no ACs exist."""
        mock_us.return_value = "US-001"
        mock_plan.return_value = {}
        mock_ids.return_value = []

        result = get_unmet_acs({})
        assert result == []


class TestGetUnmetScs:
    """Tests for get_unmet_scs function."""

    @patch(f"{VALIDATOR_MODULE}.load_release_plan")
    @patch(f"{VALIDATOR_MODULE}.get_all_scs_ids_in_feature")
    @patch(f"{VALIDATOR_MODULE}.get_current_feature_id")
    @patch(f"{VALIDATOR_MODULE}.is_sc_met")
    def test_returns_unmet_scs(self, mock_met, mock_feat, mock_ids, mock_plan):
        """Returns SC IDs that are not met."""
        mock_feat.return_value = "FEAT-001"
        mock_plan.return_value = {}
        mock_ids.return_value = ["SC-001", "SC-002"]
        mock_met.side_effect = lambda sc_id, state: sc_id == "SC-001"

        result = get_unmet_scs({})
        assert result == ["SC-002"]

    @patch(f"{VALIDATOR_MODULE}.load_release_plan")
    @patch(f"{VALIDATOR_MODULE}.get_all_scs_ids_in_feature")
    @patch(f"{VALIDATOR_MODULE}.get_current_feature_id")
    @patch(f"{VALIDATOR_MODULE}.is_sc_met")
    def test_all_met_returns_empty(self, mock_met, mock_feat, mock_ids, mock_plan):
        """Returns empty list when all SCs are met."""
        mock_feat.return_value = "FEAT-001"
        mock_plan.return_value = {}
        mock_ids.return_value = ["SC-001"]
        mock_met.return_value = True

        result = get_unmet_scs({})
        assert result == []


class TestGetUnmetEpicScs:
    """Tests for get_unmet_epic_scs function."""

    @patch(f"{VALIDATOR_MODULE}.load_release_plan")
    @patch(f"{VALIDATOR_MODULE}.find_epic")
    @patch(f"{VALIDATOR_MODULE}.get_current_epic_id")
    def test_returns_unmet_epic_scs(self, mock_epic_id, mock_find, mock_plan):
        """Returns epic SC IDs that are not met."""
        mock_epic_id.return_value = "EPIC-001"
        mock_plan.return_value = {}
        mock_find.return_value = {
            "success_criteria": [
                {"id": "ESC-001"},
                {"id": "ESC-002"},
            ]
        }

        state = {"met_epic_scs": ["ESC-001"]}
        result = get_unmet_epic_scs(state)
        assert result == ["ESC-002"]

    @patch(f"{VALIDATOR_MODULE}.load_release_plan")
    @patch(f"{VALIDATOR_MODULE}.find_epic")
    @patch(f"{VALIDATOR_MODULE}.get_current_epic_id")
    def test_no_epic_returns_empty(self, mock_epic_id, mock_find, mock_plan):
        """Returns empty list when epic has no success criteria."""
        mock_epic_id.return_value = "EPIC-001"
        mock_plan.return_value = {}
        mock_find.return_value = {}

        result = get_unmet_epic_scs({})
        assert result == []

    @patch(f"{VALIDATOR_MODULE}.load_release_plan")
    @patch(f"{VALIDATOR_MODULE}.find_epic")
    @patch(f"{VALIDATOR_MODULE}.get_current_epic_id")
    def test_all_met_returns_empty(self, mock_epic_id, mock_find, mock_plan):
        """Returns empty when all epic SCs are met."""
        mock_epic_id.return_value = "EPIC-001"
        mock_plan.return_value = {}
        mock_find.return_value = {
            "success_criteria": [{"id": "ESC-001"}]
        }

        state = {"met_epic_scs": ["ESC-001"]}
        result = get_unmet_epic_scs(state)
        assert result == []


class TestHasPendingAcValidation:
    """Tests for has_pending_ac_validation function."""

    @patch(f"{VALIDATOR_MODULE}.get_unmet_acs")
    @patch(f"{VALIDATOR_MODULE}.are_all_tasks_completed_in_user_story")
    @patch(f"{VALIDATOR_MODULE}.get_current_user_story")
    def test_true_when_tasks_done_acs_unmet(self, mock_us, mock_tasks, mock_unmet):
        """Returns True when all tasks done but ACs unmet."""
        mock_us.return_value = "US-001"
        mock_tasks.return_value = True
        mock_unmet.return_value = ["AC-001"]

        assert has_pending_ac_validation({}) is True

    @patch(f"{VALIDATOR_MODULE}.are_all_tasks_completed_in_user_story")
    @patch(f"{VALIDATOR_MODULE}.get_current_user_story")
    def test_false_when_tasks_incomplete(self, mock_us, mock_tasks):
        """Returns False when tasks are not all completed."""
        mock_us.return_value = "US-001"
        mock_tasks.return_value = False

        assert has_pending_ac_validation({}) is False

    @patch(f"{VALIDATOR_MODULE}.get_current_user_story")
    def test_false_when_no_current_us(self, mock_us):
        """Returns False when no current user story."""
        mock_us.return_value = None

        assert has_pending_ac_validation({}) is False

    @patch(f"{VALIDATOR_MODULE}.get_unmet_acs")
    @patch(f"{VALIDATOR_MODULE}.are_all_tasks_completed_in_user_story")
    @patch(f"{VALIDATOR_MODULE}.get_current_user_story")
    def test_false_when_all_acs_met(self, mock_us, mock_tasks, mock_unmet):
        """Returns False when all ACs are already met."""
        mock_us.return_value = "US-001"
        mock_tasks.return_value = True
        mock_unmet.return_value = []

        assert has_pending_ac_validation({}) is False


class TestHasPendingScValidation:
    """Tests for has_pending_sc_validation function."""

    @patch(f"{VALIDATOR_MODULE}.get_unmet_scs")
    @patch(f"{VALIDATOR_MODULE}.are_all_user_stories_completed_in_feature")
    @patch(f"{VALIDATOR_MODULE}.get_current_feature_id")
    def test_true_when_stories_done_scs_unmet(self, mock_feat, mock_stories, mock_unmet):
        """Returns True when all user stories done but SCs unmet."""
        mock_feat.return_value = "FEAT-001"
        mock_stories.return_value = True
        mock_unmet.return_value = ["SC-001"]

        assert has_pending_sc_validation({}) is True

    @patch(f"{VALIDATOR_MODULE}.are_all_user_stories_completed_in_feature")
    @patch(f"{VALIDATOR_MODULE}.get_current_feature_id")
    def test_false_when_stories_incomplete(self, mock_feat, mock_stories):
        """Returns False when user stories are not all completed."""
        mock_feat.return_value = "FEAT-001"
        mock_stories.return_value = False

        assert has_pending_sc_validation({}) is False

    @patch(f"{VALIDATOR_MODULE}.get_current_feature_id")
    def test_false_when_no_current_feature(self, mock_feat):
        """Returns False when no current feature."""
        mock_feat.return_value = None

        assert has_pending_sc_validation({}) is False


class TestHasPendingEpicScValidation:
    """Tests for has_pending_epic_sc_validation function."""

    @patch(f"{VALIDATOR_MODULE}.get_unmet_epic_scs")
    @patch(f"{VALIDATOR_MODULE}.are_all_features_completed_in_epic")
    @patch(f"{VALIDATOR_MODULE}.get_current_epic_id")
    def test_true_when_features_done_escs_unmet(self, mock_epic, mock_feats, mock_unmet):
        """Returns True when all features done but epic SCs unmet."""
        mock_epic.return_value = "EPIC-001"
        mock_feats.return_value = True
        mock_unmet.return_value = ["ESC-001"]

        assert has_pending_epic_sc_validation({}) is True

    @patch(f"{VALIDATOR_MODULE}.are_all_features_completed_in_epic")
    @patch(f"{VALIDATOR_MODULE}.get_current_epic_id")
    def test_false_when_features_incomplete(self, mock_epic, mock_feats):
        """Returns False when features are not all completed."""
        mock_epic.return_value = "EPIC-001"
        mock_feats.return_value = False

        assert has_pending_epic_sc_validation({}) is False

    @patch(f"{VALIDATOR_MODULE}.get_current_epic_id")
    def test_false_when_no_current_epic(self, mock_epic):
        """Returns False when no current epic."""
        mock_epic.return_value = None

        assert has_pending_epic_sc_validation({}) is False


class TestGetPendingValidationType:
    """Tests for get_pending_validation_type function."""

    @patch(f"{VALIDATOR_MODULE}.has_pending_epic_sc_validation")
    @patch(f"{VALIDATOR_MODULE}.has_pending_sc_validation")
    @patch(f"{VALIDATOR_MODULE}.has_pending_ac_validation")
    def test_returns_ac_first(self, mock_ac, mock_sc, mock_epic):
        """AC validation has highest priority."""
        mock_ac.return_value = True
        mock_sc.return_value = True
        mock_epic.return_value = True

        assert get_pending_validation_type({}) == "ac"

    @patch(f"{VALIDATOR_MODULE}.has_pending_epic_sc_validation")
    @patch(f"{VALIDATOR_MODULE}.has_pending_sc_validation")
    @patch(f"{VALIDATOR_MODULE}.has_pending_ac_validation")
    def test_returns_sc_when_no_ac(self, mock_ac, mock_sc, mock_epic):
        """SC validation is second priority."""
        mock_ac.return_value = False
        mock_sc.return_value = True
        mock_epic.return_value = True

        assert get_pending_validation_type({}) == "sc"

    @patch(f"{VALIDATOR_MODULE}.has_pending_epic_sc_validation")
    @patch(f"{VALIDATOR_MODULE}.has_pending_sc_validation")
    @patch(f"{VALIDATOR_MODULE}.has_pending_ac_validation")
    def test_returns_epic_sc_when_no_ac_or_sc(self, mock_ac, mock_sc, mock_epic):
        """Epic SC validation is third priority."""
        mock_ac.return_value = False
        mock_sc.return_value = False
        mock_epic.return_value = True

        assert get_pending_validation_type({}) == "epic_sc"

    @patch(f"{VALIDATOR_MODULE}.has_pending_epic_sc_validation")
    @patch(f"{VALIDATOR_MODULE}.has_pending_sc_validation")
    @patch(f"{VALIDATOR_MODULE}.has_pending_ac_validation")
    def test_returns_none_when_nothing_pending(self, mock_ac, mock_sc, mock_epic):
        """Returns None when no validation is pending."""
        mock_ac.return_value = False
        mock_sc.return_value = False
        mock_epic.return_value = False

        assert get_pending_validation_type({}) is None


class TestImports:
    """Tests for module imports."""

    def test_criteria_validator_import(self):
        """All public functions can be imported."""
        from validators.criteria_validator import (
            get_unmet_acs,
            get_unmet_scs,
            get_unmet_epic_scs,
            has_pending_ac_validation,
            has_pending_sc_validation,
            has_pending_epic_sc_validation,
            get_pending_validation_type,
        )
        assert callable(get_unmet_acs)
        assert callable(get_unmet_scs)
        assert callable(get_unmet_epic_scs)
        assert callable(has_pending_ac_validation)
        assert callable(has_pending_sc_validation)
        assert callable(has_pending_epic_sc_validation)
        assert callable(get_pending_validation_type)

    def test_validators_package_import(self):
        """Validators package can be imported."""
        import validators
        assert validators is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
