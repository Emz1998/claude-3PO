#!/usr/bin/env python3
"""Setters for release plan state management.

Provides write access to project state values.
"""

import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent))
from release_plan.utils import get_release_plan_path  # type: ignore

RELEASE_PLAN_PATH = get_release_plan_path("v0.1.0")


def _load_state() -> dict:
    """Load project state from file."""
    from release_plan.state import load_project_state  # type: ignore

    return load_project_state()


def _save_state(state: dict) -> None:
    """Save project state to file."""
    from release_plan.state import save_project_state  # type: ignore

    save_project_state(state)


# Basic property setters
def set_project_name(project_name: str, state: dict | None = None) -> None:
    """Set project_name in project state."""
    if state is None:
        state = _load_state()
    state["name"] = project_name
    _save_state(state)


def set_target_release(target_release: str, state: dict | None = None) -> None:
    """Set target_release in project state."""
    if state is None:
        state = _load_state()
    state["target_release"] = target_release
    _save_state(state)


def set_current_version(version: str, state: dict | None = None) -> None:
    """Set current_version in project state."""
    if state is None:
        state = _load_state()
    state["current_version"] = version
    _save_state(state)


def set_current_epic_id(epic_id: str, state: dict | None = None) -> None:
    """Set current_epic_id in project state."""
    if state is None:
        state = _load_state()
    state["current_epic"] = epic_id
    _save_state(state)


def set_current_feature_id(feature_id: str, state: dict | None = None) -> None:
    """Set current_feature_id in project state."""
    if state is None:
        state = _load_state()
    state["current_feature"] = feature_id
    _save_state(state)


def set_current_user_story(user_story: str, state: dict | None = None) -> None:
    """Set current_user_story_id in project state."""
    if state is None:
        state = _load_state()
    state["current_user_story"] = user_story
    _save_state(state)


def set_current_user_story_status(status: str, state: dict | None = None) -> None:
    """Set current_user_story_status in project state."""
    if state is None:
        state = _load_state()
    state["current_user_story_status"] = status
    _save_state(state)


# Collection setters
def set_current_tasks(tasks: dict, state: dict | None = None) -> None:
    """Set current_tasks in project state."""
    if state is None:
        state = _load_state()
    state["current_tasks"] = tasks
    _save_state(state)


def set_current_acs(acs: dict, state: dict | None = None) -> None:
    """Set current_acs in project state."""
    if state is None:
        state = _load_state()
    state["current_acs"] = acs
    _save_state(state)


def set_current_scs(scs: dict, state: dict | None = None) -> None:
    """Set current_scs in project state."""
    if state is None:
        state = _load_state()
    state["current_scs"] = scs
    _save_state(state)


def set_current_allowed_tasks(
    allowed_tasks: list[str], state: dict | None = None
) -> None:
    """Set current_allowed_tasks in project state."""
    if state is None:
        state = _load_state()
    state["current_allowed_tasks"] = allowed_tasks
    _save_state(state)


# Completed items setters
def set_completed_tasks(completed_tasks: list[str], state: dict | None = None) -> None:
    """Set completed_tasks in project state."""
    if state is None:
        state = _load_state()
    state["completed_tasks"] = completed_tasks
    _save_state(state)


def set_completed_user_stories(
    completed_user_stories: list[str], state: dict | None = None
) -> None:
    """Set completed_user_stories in project state."""
    if state is None:
        state = _load_state()
    state["completed_user_stories"] = completed_user_stories
    _save_state(state)


def set_completed_features(
    completed_features: list[str], state: dict | None = None
) -> None:
    """Set completed_features in project state."""
    if state is None:
        state = _load_state()
    state["completed_features"] = completed_features
    _save_state(state)


def set_completed_epics(completed_epics: list[str], state: dict | None = None) -> None:
    """Set completed_epics in project state."""
    if state is None:
        state = _load_state()
    state["completed_epics"] = completed_epics
    _save_state(state)


def set_met_acs(met_acs: list[str], state: dict | None = None) -> None:
    """Set met_acs in project state."""
    if state is None:
        state = _load_state()
    state["met_acs"] = met_acs
    _save_state(state)


def set_met_scs(met_scs: list[str], state: dict | None = None) -> None:
    """Set met_scs in project state."""
    if state is None:
        state = _load_state()
    state["met_scs"] = met_scs
    _save_state(state)


# Status setter with validation
def set_status(
    key: Literal["tasks", "acs", "scs"],
    new_status: Literal["not_started", "in_progress", "completed", "met", "unmet"],
    state: dict | None = None,
) -> None:
    """Set all status in project state with transition validation."""
    if state is None:
        state = _load_state()

    current = state.get(f"current_{key}", {})
    for current_id, current_status in current.items():
        if key == "tasks":
            if current_status == "not_started" and new_status == "in_progress":
                current[current_id] = new_status
            elif current_status == "not_started" and new_status == "completed":
                print(
                    f"{key.capitalize()} '{current_id}' cannot be completed because it is not started"
                )
                return
            elif current_status == "in_progress" and new_status == "completed":
                current[current_id] = new_status
        elif key in ("acs", "scs"):
            if current_status == new_status:
                print(f"{key.capitalize()} '{current_id}' is already {new_status}")
                return
            elif current_status == "met" and new_status == "unmet":
                current[current_id] = new_status
            elif current_status == "unmet" and new_status == "met":
                current[current_id] = new_status

    state[f"current_{key}"] = current
    _save_state(state)


def set_all_status_in_progress(state: dict | None = None) -> None:
    """Set all status to in_progress/unmet."""
    if state is None:
        state = _load_state()
    set_status("tasks", "in_progress", state)
    set_status("acs", "unmet", state)
    set_status("scs", "unmet", state)
    _save_state(state)


def set_all_status_completed(state: dict | None = None) -> None:
    """Set all status to completed/met."""
    if state is None:
        state = _load_state()
    set_status("tasks", "completed", state)
    set_status("acs", "met", state)
    set_status("scs", "met", state)
    _save_state(state)


# Reset functions
def reset_all_tasks_status(state: dict | None = None) -> None:
    """Reset all tasks status to not_started."""
    if state is None:
        state = _load_state()
    state["current_tasks"] = {
        task_id: "not_started" for task_id in state.get("current_tasks", {}).keys()
    }
    _save_state(state)


def reset_all_acs_status(state: dict | None = None) -> None:
    """Reset all acceptance criteria status to unmet."""
    if state is None:
        state = _load_state()
    state["current_acs"] = {
        ac_id: "unmet" for ac_id in state.get("current_acs", {}).keys()
    }
    _save_state(state)


def reset_all_scs_status(state: dict | None = None) -> None:
    """Reset all success criteria status to unmet."""
    if state is None:
        state = _load_state()
    state["current_scs"] = {
        sc_id: "unmet" for sc_id in state.get("current_scs", {}).keys()
    }
    _save_state(state)


def reset_all_user_story_status(state: dict | None = None) -> None:
    """Reset user story status to not_started."""
    if state is None:
        state = _load_state()
    state["current_user_story_status"] = "not_started"
    _save_state(state)
