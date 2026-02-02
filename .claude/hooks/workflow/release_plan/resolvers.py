#!/usr/bin/env python3
"""Resolvers for release plan state transitions.

Handles recording completed items and navigating between epics/features/stories.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from release_plan.utils import (  # type: ignore
    load_release_plan,
    get_release_plan_path,
    get_all_tasks_ids_in_user_story,
    get_all_acs_ids_in_user_story,
    get_next_user_story_id_in_feature,
    get_first_user_story_id_in_feature,
    get_next_feature_id_in_epic,
    get_first_feature_id_in_epic,
    get_next_epic_id,
)

from release_plan.checkers import (  # type: ignore
    is_task_completed,
    is_ac_met,
    is_sc_met,
    is_user_story_completed,
    is_feature_completed,
    is_epic_completed,
    is_task_allowed,
)

from release_plan.getters import (  # type: ignore
    get_current_user_story,
    get_current_feature_id,
    get_current_epic_id,
    get_current_tasks_ids,
    get_current_acs_ids,
    get_current_scs_ids,
)

from release_plan.new_setters import (  # type: ignore
    set_current_user_story,
    set_current_feature_id,
    set_current_epic_id,
    set_current_tasks,
    set_current_acs,
    set_current_scs,
    set_completed_tasks,
    set_completed_user_stories,
    set_completed_features,
    set_completed_epics,
    set_met_acs,
    set_met_scs,
)

RELEASE_PLAN_PATH = get_release_plan_path("v0.1.0")


def _load_state() -> dict:
    """Load project state from file."""
    from release_plan.state import load_project_state  # type: ignore
    return load_project_state()


def _save_state(state: dict) -> None:
    """Save project state to file."""
    from release_plan.state import save_project_state  # type: ignore
    save_project_state(state)


# Initializers
def initialize_tasks(
    user_story_id: str, release_plan: dict, state: dict | None = None
) -> dict:
    """Initialize tasks with allowed tasks (dependencies met, not completed)."""
    if state is None:
        state = _load_state()
    from release_plan.checkers import find_tasks_allowed_in_user_story  # type: ignore
    return {
        task: "not_started"
        for task in find_tasks_allowed_in_user_story(user_story_id, state) or []
        if not is_task_completed(task, state)
    }


def initialize_acs(user_story_id: str, release_plan: dict) -> dict:
    """Initialize acceptance criteria."""
    return {
        ac: "unmet"
        for ac in get_all_acs_ids_in_user_story(user_story_id, release_plan) or []
    }


def initialize_scs(feature_id: str, release_plan: dict) -> dict:
    """Initialize success criteria."""
    from release_plan.utils import get_all_scs_ids_in_feature  # type: ignore
    return {
        sc: "unmet"
        for sc in get_all_scs_ids_in_feature(feature_id, release_plan) or []
    }


# Refresh tasks based on completed dependencies
def refresh_current_tasks(state: dict | None = None) -> dict:
    """Refresh current_tasks with only the pending allowed tasks.

    Replaces current_tasks with tasks that:
    - Have dependencies met (allowed)
    - Are not yet completed
    """
    if state is None:
        state = _load_state()

    current_user_story_id = get_current_user_story(state)
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}

    all_tasks_ids = (
        get_all_tasks_ids_in_user_story(current_user_story_id, release_plan) or []
    )

    new_current_tasks = {}
    for task_id in all_tasks_ids:
        if is_task_completed(task_id, state):
            continue
        if is_task_allowed(task_id, state):
            new_current_tasks[task_id] = "not_started"
            print(f"Task '{task_id}' is now available")

    state["current_tasks"] = new_current_tasks
    _save_state(state)
    return new_current_tasks


# Record completed items
def record_completed_task(task_id: str, state: dict | None = None) -> bool:
    """Record a completed task and unlock dependent tasks."""
    if state is None:
        state = _load_state()
    current_completed_tasks = state.get("completed_tasks", [])

    if not is_task_completed(task_id, state):
        print(f"Task '{task_id}' is not completed")
        return False
    if task_id in current_completed_tasks:
        print(f"Task '{task_id}' is already completed")
        return False

    current_completed_tasks.append(task_id)
    set_completed_tasks(current_completed_tasks, state)

    state = _load_state()
    refresh_current_tasks(state)
    return True


def record_completed_user_story(user_story_id: str, state: dict | None = None) -> bool:
    """Record a completed user story."""
    if state is None:
        state = _load_state()
    completed_user_stories = state.get("completed_user_stories", [])

    if not is_user_story_completed(user_story_id, state):
        print(f"User story '{user_story_id}' is not completed")
        return False
    if user_story_id in completed_user_stories:
        print(f"User story '{user_story_id}' is already completed")
        return False

    completed_user_stories.append(user_story_id)
    set_completed_user_stories(completed_user_stories, state)
    return True


def record_completed_feature(feature_id: str, state: dict | None = None) -> bool:
    """Record a completed feature."""
    if state is None:
        state = _load_state()
    completed_features = state.get("completed_features", [])

    if feature_id in completed_features:
        print(f"Feature '{feature_id}' is already completed")
        return False
    if not is_feature_completed(feature_id, state):
        print(f"Feature '{feature_id}' is not completed")
        return False

    completed_features.append(feature_id)
    set_completed_features(completed_features, state)
    return True


def record_completed_epic(epic_id: str, state: dict | None = None) -> bool:
    """Record a completed epic."""
    if state is None:
        state = _load_state()
    completed_epics = state.get("completed_epics", [])

    if epic_id in completed_epics:
        print(f"Epic '{epic_id}' is already completed")
        return False
    if not is_epic_completed(epic_id, state):
        print(f"Epic '{epic_id}' is not completed")
        return False

    completed_epics.append(epic_id)
    set_completed_epics(completed_epics, state)
    return True


def record_met_ac(ac_id: str, state: dict | None = None) -> bool:
    """Record a met acceptance criterion."""
    if state is None:
        state = _load_state()
    met_acs = state.get("met_acs", [])

    if not is_ac_met(ac_id, state):
        print(f"Acceptance criterion '{ac_id}' is not met")
        return False
    if ac_id in met_acs:
        print(f"Acceptance criterion '{ac_id}' is already met")
        return False

    met_acs.append(ac_id)
    set_met_acs(met_acs, state)
    return True


def record_met_sc(sc_id: str, state: dict | None = None) -> bool:
    """Record a met success criterion."""
    if state is None:
        state = _load_state()
    met_scs = state.get("met_scs", [])

    if not is_sc_met(sc_id, state):
        print(f"Success criterion '{sc_id}' is not met")
        return False
    if sc_id in met_scs:
        print(f"Success criterion '{sc_id}' is already met")
        return False

    met_scs.append(sc_id)
    set_met_scs(met_scs, state)
    return True


# Batch resolvers
def resolve_tasks(state: dict | None = None) -> bool:
    """Resolve all completed tasks."""
    if state is None:
        state = _load_state()
    current_tasks_ids = get_current_tasks_ids(state) or []
    for task_id in current_tasks_ids:
        record_completed_task(task_id, state)
    return True


def resolve_completed_acs(state: dict | None = None) -> bool:
    """Resolve all met acceptance criteria."""
    if state is None:
        state = _load_state()
    current_acs_ids = get_current_acs_ids(state) or []
    for ac_id in current_acs_ids:
        record_met_ac(ac_id, state)
    return True


def resolve_completed_scs(state: dict | None = None) -> bool:
    """Resolve all met success criteria."""
    if state is None:
        state = _load_state()
    current_scs_ids = get_current_scs_ids(state) or []
    for sc_id in current_scs_ids:
        record_met_sc(sc_id, state)
    return True


# Complex resolvers with navigation
def resolve_user_story(state: dict | None = None) -> bool:
    """Resolve user story with proper feature/epic hierarchy navigation."""
    resolve_tasks(state)
    state = _load_state()
    resolve_completed_acs(state)
    state = _load_state()
    resolve_completed_scs(state)
    state = _load_state()

    current_user_story_id = get_current_user_story(state)
    if not is_user_story_completed(current_user_story_id, state):
        print(f"User story '{current_user_story_id}' is not completed")
        return False

    record_completed_user_story(current_user_story_id, state)
    state = _load_state()

    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    current_feature_id = get_current_feature_id(state)
    current_epic_id = get_current_epic_id(state)

    # Check for next user story in SAME feature
    next_us_in_feature = get_next_user_story_id_in_feature(
        current_user_story_id, current_feature_id, release_plan
    )

    if next_us_in_feature:
        set_current_user_story(next_us_in_feature, state)
        state = _load_state()
        new_tasks = initialize_tasks(next_us_in_feature, release_plan, state)
        new_acs = initialize_acs(next_us_in_feature, release_plan)
        set_current_tasks(new_tasks, state)
        state = _load_state()
        set_current_acs(new_acs, state)
        print(f"Moved to next user story '{next_us_in_feature}' in feature '{current_feature_id}'")
        return True

    # Last user story in feature - need to transition to next feature
    if is_feature_completed(current_feature_id, state):
        record_completed_feature(current_feature_id, state)
        state = _load_state()

    next_feature_in_epic = get_next_feature_id_in_epic(
        current_feature_id, current_epic_id, release_plan
    )

    if next_feature_in_epic:
        set_current_feature_id(next_feature_in_epic, state)
        state = _load_state()
        first_us = get_first_user_story_id_in_feature(next_feature_in_epic, release_plan)
        if first_us:
            set_current_user_story(first_us, state)
            state = _load_state()
            new_tasks = initialize_tasks(first_us, release_plan, state)
            new_acs = initialize_acs(first_us, release_plan)
            new_scs = initialize_scs(next_feature_in_epic, release_plan)
            set_current_tasks(new_tasks, state)
            state = _load_state()
            set_current_acs(new_acs, state)
            state = _load_state()
            set_current_scs(new_scs, state)
        print(f"Moved to next feature '{next_feature_in_epic}' in epic '{current_epic_id}'")
        return True

    # Last feature in epic - need to transition to next epic
    if is_epic_completed(current_epic_id, state):
        record_completed_epic(current_epic_id, state)
        state = _load_state()

    next_epic = get_next_epic_id(current_epic_id, release_plan)
    if next_epic:
        set_current_epic_id(next_epic, state)
        state = _load_state()
        first_feature = get_first_feature_id_in_epic(next_epic, release_plan)
        if first_feature:
            set_current_feature_id(first_feature, state)
            state = _load_state()
            first_us = get_first_user_story_id_in_feature(first_feature, release_plan)
            if first_us:
                set_current_user_story(first_us, state)
                state = _load_state()
                new_tasks = initialize_tasks(first_us, release_plan, state)
                new_acs = initialize_acs(first_us, release_plan)
                new_scs = initialize_scs(first_feature, release_plan)
                set_current_tasks(new_tasks, state)
                state = _load_state()
                set_current_acs(new_acs, state)
                state = _load_state()
                set_current_scs(new_scs, state)
        print(f"Moved to next epic '{next_epic}'")
        return True

    print("Release plan completed!")
    return True


def resolve_feature(state: dict | None = None) -> bool:
    """Resolve feature with proper epic hierarchy navigation."""
    if state is None:
        state = _load_state()
    resolve_user_story(state)
    state = _load_state()

    current_feature_id = get_current_feature_id(state)
    current_epic_id = get_current_epic_id(state)

    if not is_feature_completed(current_feature_id, state):
        print(f"Feature '{current_feature_id}' is not completed")
        return False

    record_completed_feature(current_feature_id, state)
    state = _load_state()

    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    next_feature_in_epic = get_next_feature_id_in_epic(
        current_feature_id, current_epic_id, release_plan
    )

    if next_feature_in_epic:
        set_current_feature_id(next_feature_in_epic, state)
        state = _load_state()
        first_us = get_first_user_story_id_in_feature(next_feature_in_epic, release_plan)
        if first_us:
            set_current_user_story(first_us, state)
            state = _load_state()
            new_tasks = initialize_tasks(first_us, release_plan, state)
            new_acs = initialize_acs(first_us, release_plan)
            new_scs = initialize_scs(next_feature_in_epic, release_plan)
            set_current_tasks(new_tasks, state)
            state = _load_state()
            set_current_acs(new_acs, state)
            state = _load_state()
            set_current_scs(new_scs, state)
        print(f"Feature '{current_feature_id}' resolved to '{next_feature_in_epic}'")
        return True

    # Last feature in epic
    if is_epic_completed(current_epic_id, state):
        record_completed_epic(current_epic_id, state)
        state = _load_state()

    next_epic = get_next_epic_id(current_epic_id, release_plan)
    if next_epic:
        set_current_epic_id(next_epic, state)
        state = _load_state()
        first_feature = get_first_feature_id_in_epic(next_epic, release_plan)
        if first_feature:
            set_current_feature_id(first_feature, state)
            state = _load_state()
            first_us = get_first_user_story_id_in_feature(first_feature, release_plan)
            if first_us:
                set_current_user_story(first_us, state)
                state = _load_state()
                new_tasks = initialize_tasks(first_us, release_plan, state)
                new_acs = initialize_acs(first_us, release_plan)
                new_scs = initialize_scs(first_feature, release_plan)
                set_current_tasks(new_tasks, state)
                state = _load_state()
                set_current_acs(new_acs, state)
                state = _load_state()
                set_current_scs(new_scs, state)
        print(f"Feature '{current_feature_id}' resolved, moved to epic '{next_epic}'")
        return True

    print(f"Feature '{current_feature_id}' resolved. Release plan completed!")
    return True


def resolve_epic(state: dict | None = None) -> bool:
    """Resolve epic with proper hierarchy navigation."""
    if state is None:
        state = _load_state()
    resolve_feature(state)
    state = _load_state()

    current_epic_id = get_current_epic_id(state)
    if not is_epic_completed(current_epic_id, state):
        print(f"Epic '{current_epic_id}' is not completed")
        return False

    record_completed_epic(current_epic_id, state)
    state = _load_state()

    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    next_epic = get_next_epic_id(current_epic_id, release_plan)

    if next_epic:
        set_current_epic_id(next_epic, state)
        state = _load_state()
        first_feature = get_first_feature_id_in_epic(next_epic, release_plan)
        if first_feature:
            set_current_feature_id(first_feature, state)
            state = _load_state()
            first_us = get_first_user_story_id_in_feature(first_feature, release_plan)
            if first_us:
                set_current_user_story(first_us, state)
                state = _load_state()
                new_tasks = initialize_tasks(first_us, release_plan, state)
                new_acs = initialize_acs(first_us, release_plan)
                new_scs = initialize_scs(first_feature, release_plan)
                set_current_tasks(new_tasks, state)
                state = _load_state()
                set_current_acs(new_acs, state)
                state = _load_state()
                set_current_scs(new_scs, state)
        print(f"Epic '{current_epic_id}' resolved to '{next_epic}'")
        return True

    print(f"Epic '{current_epic_id}' resolved. Release plan completed!")
    return True


def resolve_state(state: dict | None = None) -> None:
    """Resolve entire project state."""
    if state is None:
        state = _load_state()
    resolve_epic(state)
    print("State resolved")


# Utility
def increment_id(some_id: str) -> str:
    """Increment an ID (e.g., US-001 -> US-002)."""
    num = int(some_id[-3:]) + 1
    return some_id[:-3] + str(num).zfill(3)
