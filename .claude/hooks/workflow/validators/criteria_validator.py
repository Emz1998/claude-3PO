#!/usr/bin/env python3
"""Criteria validation detection logic.

Determines when AC, SC, or epic SC validation is pending based on
task/story/feature completion status vs criteria status.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from release_plan.checkers import (  # type: ignore
    are_all_tasks_completed_in_user_story,
    are_all_user_stories_completed_in_feature,
    are_all_features_completed_in_epic,
    is_ac_met,
    is_sc_met,
)
from release_plan.getters import (  # type: ignore
    get_current_user_story,
    get_current_feature_id,
    get_current_epic_id,
    get_current_acs_ids,
    get_current_scs_ids,
)
from release_plan.utils import (  # type: ignore
    load_release_plan,
    get_release_plan_path,
    get_all_acs_ids_in_user_story,
    get_all_scs_ids_in_feature,
    find_epic,
)

RELEASE_PLAN_PATH = get_release_plan_path("v0.1.0")


def _load_state() -> dict:
    """Load project state from file."""
    from release_plan.state import load_project_state  # type: ignore
    return load_project_state()


def get_unmet_acs(state: dict | None = None) -> list[str]:
    """Return unmet AC IDs for the current user story."""
    if state is None:
        state = _load_state()

    current_us = get_current_user_story(state)
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    all_ac_ids = get_all_acs_ids_in_user_story(current_us, release_plan) or []

    return [ac_id for ac_id in all_ac_ids if not is_ac_met(ac_id, state)]


def get_unmet_scs(state: dict | None = None) -> list[str]:
    """Return unmet SC IDs for the current feature."""
    if state is None:
        state = _load_state()

    current_feature = get_current_feature_id(state)
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    all_sc_ids = get_all_scs_ids_in_feature(current_feature, release_plan) or []

    return [sc_id for sc_id in all_sc_ids if not is_sc_met(sc_id, state)]


def get_unmet_epic_scs(state: dict | None = None) -> list[str]:
    """Return unmet SC IDs for the current epic."""
    if state is None:
        state = _load_state()

    current_epic_id = get_current_epic_id(state)
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    epic = find_epic(current_epic_id, release_plan) or {}
    epic_scs = epic.get("success_criteria", [])

    met_scs = state.get("met_epic_scs", [])
    return [
        sc.get("id", "")
        for sc in epic_scs
        if sc.get("id", "") not in met_scs
    ]


def has_pending_ac_validation(state: dict | None = None) -> bool:
    """All tasks in current US completed, but not all ACs met."""
    if state is None:
        state = _load_state()

    current_us = get_current_user_story(state)
    if not current_us:
        return False

    if not are_all_tasks_completed_in_user_story(current_us, state):
        return False

    return len(get_unmet_acs(state)) > 0


def has_pending_sc_validation(state: dict | None = None) -> bool:
    """All user stories in current feature completed, but not all SCs met."""
    if state is None:
        state = _load_state()

    current_feature = get_current_feature_id(state)
    if not current_feature:
        return False

    if not are_all_user_stories_completed_in_feature(current_feature, state):
        return False

    return len(get_unmet_scs(state)) > 0


def has_pending_epic_sc_validation(state: dict | None = None) -> bool:
    """All features in current epic completed, but not all epic SCs met."""
    if state is None:
        state = _load_state()

    current_epic = get_current_epic_id(state)
    if not current_epic:
        return False

    if not are_all_features_completed_in_epic(current_epic, state):
        return False

    return len(get_unmet_epic_scs(state)) > 0


def get_pending_validation_type(state: dict | None = None) -> str | None:
    """Return the type of pending validation, or None.

    Returns: "ac", "sc", "epic_sc", or None
    Priority: ac > sc > epic_sc (check innermost first)
    """
    if state is None:
        state = _load_state()

    if has_pending_ac_validation(state):
        return "ac"
    if has_pending_sc_validation(state):
        return "sc"
    if has_pending_epic_sc_validation(state):
        return "epic_sc"
    return None
