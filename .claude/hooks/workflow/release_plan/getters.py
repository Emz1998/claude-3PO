#!/usr/bin/env python3
"""Getters for release plan state management.

Provides read-only access to project state values.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.json import load_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from release_plan.utils import (  # type: ignore
    load_release_plan,
    get_release_plan_path,
    get_task_dependencies_ids,
)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
PROJECT_STATE_FILE_PATH = PROJECT_ROOT / "project" / "state.json"
RELEASE_PLAN_PATH = get_release_plan_path("v0.1.0")


def _load_state() -> dict:
    """Load project state from file."""
    from release_plan.state import load_project_state  # type: ignore
    return load_project_state()


# Basic property getters
def get_project_name(state: dict | None = None) -> str:
    """Retrieve project_name from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("name", "")


def get_target_release(state: dict | None = None) -> str:
    """Retrieve target_release from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("target_release", "")


def get_current_version(state: dict | None = None) -> str:
    """Retrieve current_version from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("current_version", "")


def get_current_epic_id(state: dict | None = None) -> str:
    """Retrieve current_epic_id from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("current_epic", "")


def get_current_feature_id(state: dict | None = None) -> str:
    """Retrieve current_feature_id from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("current_feature", "")


def get_current_user_story(state: dict | None = None) -> str:
    """Retrieve current_user_story from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("current_user_story", "")


# Tasks getters
def get_current_tasks(state: dict | None = None) -> dict:
    """Retrieve current_tasks from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("current_tasks", {})


def get_current_tasks_ids(state: dict | None = None) -> list[str]:
    """Retrieve current_tasks_ids from project state."""
    if state is None:
        state = _load_state()
    return list(((state or {}).get("current_tasks") or {}).keys())


def get_current_task_dependencies(task_id: str, state: dict | None = None) -> list[str]:
    """Get dependencies for a task."""
    if state is None:
        state = _load_state()
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    return get_task_dependencies_ids(task_id, release_plan) or []


# Acceptance criteria getters
def get_current_acs(state: dict | None = None) -> dict:
    """Retrieve current_acs from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("current_acs", {})


def get_current_acs_ids(state: dict | None = None) -> list[str]:
    """Retrieve current_acs_ids from project state."""
    if state is None:
        state = _load_state()
    return list(((state or {}).get("current_acs") or {}).keys())


# Success criteria getters
def get_current_scs(state: dict | None = None) -> dict:
    """Retrieve current_scs from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("current_scs", {})


def get_current_scs_ids(state: dict | None = None) -> list[str]:
    """Retrieve current_scs_ids from project state."""
    if state is None:
        state = _load_state()
    return list(((state or {}).get("current_scs") or {}).keys())


# Allowed tasks getter
def get_current_allowed_tasks(state: dict | None = None) -> list[str]:
    """Retrieve current_allowed_tasks from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("current_allowed_tasks", [])


# Completed items getters
def get_completed_tasks(state: dict | None = None) -> list[str]:
    """Retrieve completed_tasks from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("completed_tasks", [])


def get_completed_user_stories(state: dict | None = None) -> list[str]:
    """Retrieve completed_user_stories from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("completed_user_stories", [])


def get_completed_features(state: dict | None = None) -> list[str]:
    """Retrieve completed_features from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("completed_features", [])


def get_completed_epics(state: dict | None = None) -> list[str]:
    """Retrieve completed_epics from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("completed_epics", [])


def get_met_acs(state: dict | None = None) -> list[str]:
    """Retrieve met_acs from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("met_acs", [])


def get_met_scs(state: dict | None = None) -> list[str]:
    """Retrieve met_scs from project state."""
    if state is None:
        state = _load_state()
    return (state or {}).get("met_scs", [])


# Tasks with completed dependencies
def get_tasks_with_completed_deps(
    *task_ids: str,
    release_plan: dict | None = None,
    state: dict | None = None,
) -> list[str]:
    """Retrieve tasks with completed dependencies from project state."""
    from release_plan.checkers import are_task_deps_completed  # type: ignore

    if not release_plan:
        release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    if state is None:
        state = _load_state()

    return [
        task_id
        for task_id in task_ids
        if are_task_deps_completed(task_id, release_plan, state)
    ]
