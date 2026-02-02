#!/usr/bin/env python3
"""Checkers for release plan state validation.

Provides boolean checks for completion and meeting criteria.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from release_plan.utils import (  # type: ignore
    load_release_plan,
    get_release_plan_path,
    get_all_tasks_ids_in_user_story,
    get_all_acs_ids_in_user_story,
    get_all_user_story_ids_in_feature,
    get_all_scs_ids_in_feature,
    get_all_features_ids_in_epic,
    get_task_dependencies_ids,
)

RELEASE_PLAN_PATH = get_release_plan_path("v0.1.0")


def _load_state() -> dict:
    """Load project state from file."""
    from release_plan.state import load_project_state  # type: ignore
    return load_project_state()


# Single item checkers
def is_task_completed(task_id: str, state: dict | None = None) -> bool:
    """Check if task is completed."""
    if state is None:
        state = _load_state()

    if task_id in state.get("completed_tasks", []):
        return True
    return state.get("current_tasks", {}).get(task_id, "") == "completed"


def is_ac_met(ac_id: str, state: dict | None = None) -> bool:
    """Check if acceptance criterion is met."""
    if state is None:
        state = _load_state()
    if ac_id in state.get("met_acs", []):
        return True
    return state.get("current_acs", {}).get(ac_id, "") == "met"


def is_sc_met(sc_id: str, state: dict | None = None) -> bool:
    """Check if success criterion is met."""
    if state is None:
        state = _load_state()
    if sc_id in state.get("met_scs", []):
        return True
    return state.get("current_scs", {}).get(sc_id, "") == "met"


# Compound checkers
def is_user_story_completed(user_story_id: str, state: dict | None = None) -> bool:
    """Check if user story is completed.

    Checks ALL tasks and ACs in the user story from the release plan,
    not just the currently tracked ones in state.
    """
    if state is None:
        state = _load_state()
    if user_story_id in state.get("completed_user_stories", []):
        return True

    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    all_tasks_ids = get_all_tasks_ids_in_user_story(user_story_id, release_plan) or []
    all_acs_ids = get_all_acs_ids_in_user_story(user_story_id, release_plan) or []

    if not all_tasks_ids and not all_acs_ids:
        return False

    tasks_completed = all(is_task_completed(task_id, state) for task_id in all_tasks_ids)
    ac_met = all(is_ac_met(ac_id, state) for ac_id in all_acs_ids)
    return tasks_completed and ac_met


def is_feature_completed(feature_id: str, state: dict | None = None) -> bool:
    """Check if feature is completed.

    Checks ALL user stories and SCs from the release plan,
    not just the currently tracked ones in state.
    """
    if state is None:
        state = _load_state()
    completed_features = state.get("completed_features", [])
    if feature_id in completed_features:
        return True

    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    user_story_ids = get_all_user_story_ids_in_feature(feature_id, release_plan) or []

    if not user_story_ids:
        return False

    completed_user_stories = state.get("completed_user_stories", [])
    all_user_stories_completed = all(
        user_story_id in completed_user_stories for user_story_id in user_story_ids
    )

    all_scs_ids = get_all_scs_ids_in_feature(feature_id, release_plan) or []
    all_scs_met = all(is_sc_met(sc_id, state) for sc_id in all_scs_ids)

    if not all_scs_ids:
        return all_user_stories_completed
    return all_user_stories_completed and all_scs_met


def is_epic_completed(epic_id: str, state: dict | None = None) -> bool:
    """Check if epic is completed."""
    if state is None:
        state = _load_state()
    completed_epics = state.get("completed_epics", [])
    if epic_id in completed_epics:
        return True

    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    feature_ids = get_all_features_ids_in_epic(epic_id, release_plan) or []

    if not feature_ids:
        return False

    completed_features = state.get("completed_features", [])
    return all(feature_id in completed_features for feature_id in feature_ids)


# Dependency checkers
def are_task_deps_completed(
    task_id: str, release_plan: dict | None = None, state: dict | None = None
) -> bool:
    """Check if task dependencies are completed."""
    if state is None:
        state = _load_state()
    if release_plan is None:
        release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    deps = get_task_dependencies_ids(task_id, release_plan) or []
    return all(is_task_completed(dep_id, state) for dep_id in deps)


def is_task_allowed(task_id: str, state: dict | None = None) -> bool:
    """Check if a task is allowed (dependencies met)."""
    if state is None:
        state = _load_state()
    from release_plan.getters import get_current_task_dependencies  # type: ignore
    deps = get_current_task_dependencies(task_id, state) or []
    return all(is_task_completed(dep_id, state) for dep_id in deps)


# Finder helpers
def find_tasks_allowed_in_user_story(
    user_story_id: str, state: dict | None = None
) -> list[str]:
    """Find all allowed (deps met) tasks in a user story."""
    if state is None:
        state = _load_state()
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    tasks = get_all_tasks_ids_in_user_story(user_story_id, release_plan) or []
    return [task_id for task_id in tasks if is_task_allowed(task_id, state)]
