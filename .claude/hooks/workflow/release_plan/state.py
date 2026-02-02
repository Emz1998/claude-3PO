import sys
from datetime import datetime
from pathlib import Path
from typing import Literal
from filelock import FileLock


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.json import load_json, save_json  # type: ignore


sys.path.insert(0, str(Path(__file__).parent.parent))
from release_plan.utils import (  # type: ignore
    load_release_plan,
    get_release_plan_path,
    get_all_acs_ids_in_user_story,
    get_all_scs_ids_in_feature,
    get_all_tasks_ids_in_user_story,
    get_all_user_story_ids_in_feature,
    get_all_features_ids_in_epic,
    get_task_dependencies_ids,
    get_next_user_story_id_in_feature,
    get_first_user_story_id_in_feature,
    get_next_feature_id_in_epic,
    get_first_feature_id_in_epic,
    get_next_epic_id,
    get_first_epic_id,
    find_feature_id_of_user_story,
    find_epic_id_of_feature,
    PROJECT_ROOT,
)

PROJECT_STATE_FILE_PATH = PROJECT_ROOT / "project" / "state.json"
TARGET_RELEASE = "2025-01-15"
PROJECT_NAME = "Avaris - NBA Betting Analytics Platform"
CURRENT_VERSION = "v0.1.0"

RELEASE_PLAN_PATH = get_release_plan_path("v0.1.0")
STATE_LOCK = FileLock(PROJECT_STATE_FILE_PATH.with_suffix(".lock"))


def load_project_state() -> dict:
    """Load project state from status.json."""
    with STATE_LOCK:
        return load_json(PROJECT_STATE_FILE_PATH)


def save_project_state(
    state: dict | None = None, file_path: Path | None = None
) -> bool:
    if state is None:
        state = load_project_state() or {}
    if file_path is None:
        file_path = PROJECT_STATE_FILE_PATH
    file_path.parent.mkdir(parents=True, exist_ok=True)
    state["updated"] = datetime.now().isoformat()
    with STATE_LOCK:
        save_json(state, file_path)
    return True


# Initializers


def initialize_tasks(
    user_story_id: str, release_plan: dict, state: dict | None = None
) -> dict:
    """Initialize tasks with allowed tasks (dependencies met, not completed)."""
    if state is None:
        state = load_project_state() or {}
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
    return {
        sc: "unmet" for sc in get_all_scs_ids_in_feature(feature_id, release_plan) or []
    }


def initialize_project_state() -> None:
    """Initialize project state."""
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    current_epic_id = "EPIC-001"
    current_feature_id = "FEAT-001"
    current_user_story_id = "US-001"
    # Pass empty state for fresh initialization (no completed tasks)
    empty_state: dict = {"completed_tasks": []}
    current_tasks = initialize_tasks(current_user_story_id, release_plan, empty_state)
    current_acs = initialize_acs(current_user_story_id, release_plan)
    current_scs = initialize_scs(current_feature_id, release_plan)

    default_state = {
        "name": PROJECT_NAME,
        "target_release": TARGET_RELEASE,
        "current_version": CURRENT_VERSION,
        "current_epic": current_epic_id,
        "current_feature": current_feature_id,
        "current_user_story": current_user_story_id,
        "current_tasks": current_tasks,
        "current_acs": current_acs,
        "current_scs": current_scs,
        "completed_user_stories": [],
        "completed_features": [],
        "updated": datetime.now().isoformat(),
    }
    save_project_state(default_state)


def test_project_state() -> None:
    """Initialize project state."""
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    current_epic_id = "EPIC-001"
    current_feature_id = "FEAT-001"
    current_user_story_id = "US-001"
    # Pass empty state for fresh initialization (no completed tasks)
    empty_state: dict = {"completed_tasks": []}
    current_tasks = initialize_tasks(current_user_story_id, release_plan, empty_state)
    current_acs = initialize_acs(current_user_story_id, release_plan)
    current_scs = initialize_scs(current_feature_id, release_plan)

    default_state = {
        "name": PROJECT_NAME,
        "target_release": TARGET_RELEASE,
        "current_version": CURRENT_VERSION,
        "current_epic": current_epic_id,
        "current_feature": current_feature_id,
        "current_user_story": current_user_story_id,
        "current_tasks": current_tasks,
        "current_acs": current_acs,
        "current_scs": current_scs,
        "completed_tasks": [],
        "met_acs": [],
        "met_scs": [],
        "completed_user_stories": [],
        "completed_features": [],
        "completed_epics": [],
        "updated": datetime.now().isoformat(),
    }
    save_project_state(default_state)
    set_all_status_in_progress(default_state)
    set_all_status_completed(default_state)


# Setters


def set_project_name(project_name: str, state: dict | None = None) -> None:
    """Set project_name in project state."""
    if state is None:
        state = load_project_state() or {}
    state["name"] = project_name
    save_project_state(state)


def set_target_release(target_release: str, state: dict | None = None) -> None:
    """Set target_release in project state."""
    if state is None:
        state = load_project_state() or {}
    state["target_release"] = target_release
    save_project_state(state)


def set_current_version(version: str, state: dict | None = None) -> None:
    """Set current_version in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_version"] = version
    save_project_state(state)


def set_current_epic_id(epic_id: str, state: dict | None = None) -> None:
    """Set current_epic_id in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_epic"] = epic_id
    save_project_state(state)


def set_current_feature_id(feature_id: str, state: dict | None = None) -> None:
    """Set current_feature_id in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_feature"] = feature_id
    save_project_state(state)


def set_current_user_story(user_story: str, state: dict | None = None) -> None:
    """Set current_user_story_id in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_user_story"] = user_story
    save_project_state(state)


def set_current_user_story_status(status: str, state: dict | None = None) -> None:
    """Set current_user_story_status in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_user_story_status"] = status
    save_project_state(state)


def set_current_tasks(tasks: dict, state: dict | None = None) -> None:
    """Set current_tasks in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_tasks"] = tasks
    save_project_state(state)


def set_current_acs(acs: dict, state: dict | None = None) -> None:
    """Set current_acs in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_acs"] = acs
    save_project_state(state)


def set_current_scs(scs: dict, state: dict | None = None) -> None:
    """Set current_scs in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_scs"] = scs
    save_project_state(state)


def set_status(
    key: Literal["tasks", "acs", "scs"],
    new_status: Literal["not_started", "in_progress", "completed", "met", "unmet"],
    state: dict | None = None,
) -> None:
    """Set all status in project state."""
    if state is None:
        state = load_project_state() or {}
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
        elif key == "acs" or key == "scs":
            if current_status == new_status:
                print(f"{key.capitalize()} '{current_id}' is already {new_status}")
                return
            elif current_status == "met" and new_status == "unmet":
                current[current_id] = new_status
            elif current_status == "unmet" and new_status == "met":
                current[current_id] = new_status

    state[f"current_{key}"] = current
    save_project_state(state)


def set_all_status_in_progress(state: dict | None = None) -> None:
    """Set all status in project state."""
    if state is None:
        state = load_project_state() or {}
    set_status("tasks", "in_progress", state)
    set_status("acs", "unmet", state)
    set_status("scs", "unmet", state)
    save_project_state(state)


def set_all_status_completed(state: dict | None = None) -> None:
    """Set all status in project state."""
    if state is None:
        state = load_project_state() or {}
    set_status("tasks", "completed", state)
    set_status("acs", "met", state)
    set_status("scs", "met", state)
    save_project_state(state)


def set_current_allowed_tasks(
    allowed_tasks: list[str], state: dict | None = None
) -> None:
    """Set current_allowed_tasks in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_allowed_tasks"] = allowed_tasks
    save_project_state(state)


def set_completed_user_stories(
    completed_user_stories: list[str], state: dict | None = None
) -> None:
    """Set completed_user_stories in project state."""
    if state is None:
        state = load_project_state() or {}
    state["completed_user_stories"] = completed_user_stories
    save_project_state(state)


def set_completed_features(
    completed_features: list[str], state: dict | None = None
) -> None:
    """Set completed_features in project state."""
    if state is None:
        state = load_project_state() or {}
    state["completed_features"] = completed_features
    save_project_state(state)


def set_completed_tasks(completed_tasks: list[str], state: dict | None = None) -> None:
    """Set completed_tasks in project state."""
    if state is None:
        state = load_project_state() or {}
    state["completed_tasks"] = completed_tasks
    save_project_state(state)


def set_met_acs(met_acs: list[str], state: dict | None = None) -> None:
    """Set met_acs in project state."""
    if state is None:
        state = load_project_state() or {}
    state["met_acs"] = met_acs
    save_project_state(state)


def set_met_scs(met_scs: list[str], state: dict | None = None) -> None:
    """Set met_scs in project state."""
    if state is None:
        state = load_project_state() or {}
    state["met_scs"] = met_scs
    save_project_state(state)


def set_completed_epics(completed_epics: list[str], state: dict | None = None) -> None:
    """Set completed_epics in project state."""
    if state is None:
        state = load_project_state() or {}
    state["completed_epics"] = completed_epics
    save_project_state(state)


# Getters


def get_project_name(state: dict) -> str:
    """Retrieve project_name from project state."""
    state = state or {}
    return state.get("name", "")


def get_target_release(state: dict) -> str:
    """Retrieve target_release from project state."""
    state = state or {}
    return state.get("target_release", "")


def get_current_version(state: dict) -> str:
    """Retrieve current_version from project state."""
    state = state or {}
    return state.get("current_version", "")


def get_current_epic_id(state: dict) -> str:
    """Retrieve current_epic_id from project state."""
    state = state or {}
    return state.get("current_epic", "")


def get_current_feature_id(state: dict) -> str:
    """Retrieve current_feature_id from project state."""
    state = state or {}
    return state.get("current_feature", "")


def get_current_user_story(state: dict) -> str:
    """Retrieve current_user_story from project state."""
    state = state or {}
    return state.get("current_user_story", "")


# ---


def get_current_tasks(state: dict) -> dict:
    """Retrieve current_tasks from project state."""
    state = state or {}
    return state.get("current_tasks", {})


def get_current_tasks_ids(state: dict) -> list[str]:
    """Retrieve current_tasks_ids from project state."""
    state = state or {}
    return list((state.get("current_tasks") or {}).keys())


def get_current_task_dependencies(task_id: str, state: dict | None = None) -> list[str]:
    if state is None:
        state = load_project_state() or {}
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    return get_task_dependencies_ids(task_id, release_plan) or []


# ---


def get_current_acs(state: dict) -> dict:
    """Retrieve current_acs from project state."""
    state = state or {}
    return state.get("current_acs", {})


def get_current_acs_ids(state: dict) -> list[str]:
    """Retrieve current_acs_ids from project state."""
    state = state or {}
    return list((state.get("current_acs") or {}).keys())


# ---


def get_current_scs(state: dict) -> dict:
    """Retrieve current_scs from project state."""
    state = state or {}
    return state.get("current_scs", {})


def get_current_scs_ids(state: dict) -> list[str]:
    """Retrieve current_scs_ids from project state."""
    state = state or {}
    return list((state.get("current_scs") or {}).keys())


# ---


def get_current_allowed_tasks(state: dict) -> list[str]:
    """Retrieve current_allowed_tasks from project state."""
    state = state or {}
    return state.get("current_allowed_tasks", [])


# ---


def get_tasks_with_completed_deps(
    *task_ids: str,
    release_plan: dict | None = None,
    state: dict | None = None,
) -> list[str]:
    """Retrieve tasks with completed dependencies from project state."""
    if not release_plan:
        release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    if state is None:
        state = load_project_state() or {}

    return [
        task_id
        for task_id in task_ids
        if are_task_deps_completed(task_id, release_plan, state)
    ]


# ----------------- Helpers -----------------


# Checkers


# Single checkers


def is_task_completed(task_id: str, state: dict | None = None) -> bool:
    """Check if task is completed."""
    if state is None:
        state = load_project_state() or {}

    if task_id in state.get("completed_tasks", []):
        return True
    return state.get("current_tasks", {}).get(task_id, "") == "completed"


def is_ac_met(ac_id: str, state: dict | None = None) -> bool:
    """Check if acceptance criterion is met."""
    if state is None:
        state = load_project_state() or {}
    if ac_id in state.get("met_acs", []):
        return True
    return state.get("current_acs", {}).get(ac_id, "") == "met"


def is_sc_met(sc_id: str, state: dict | None = None) -> bool:
    """Check if success criterion is met."""
    if state is None:
        state = load_project_state() or {}
    if sc_id in state.get("met_scs", []):
        return True
    return state.get("current_scs", {}).get(sc_id, "") == "met"


def is_user_story_completed(user_story_id: str, state: dict | None = None) -> bool:
    """Check if user story is completed.

    Checks ALL tasks and ACs in the user story from the release plan,
    not just the currently tracked ones in state.
    """
    if state is None:
        state = load_project_state() or {}
    if user_story_id in state.get("completed_user_stories", []):
        return True

    # Get ALL tasks and ACs from the release plan, not just current_tasks
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    all_tasks_ids = get_all_tasks_ids_in_user_story(user_story_id, release_plan) or []
    all_acs_ids = get_all_acs_ids_in_user_story(user_story_id, release_plan) or []

    # Empty lists mean no tasks/acs exist, so not completed
    if not all_tasks_ids and not all_acs_ids:
        return False

    tasks_completed = all(
        is_task_completed(task_id, state) for task_id in all_tasks_ids
    )
    ac_met = all(is_ac_met(ac_id, state) for ac_id in all_acs_ids)
    return tasks_completed and ac_met


def is_feature_completed(feature_id: str, state: dict | None = None) -> bool:
    """Check if feature is completed.

    Checks ALL user stories and SCs from the release plan,
    not just the currently tracked ones in state.
    """
    if state is None:
        state = load_project_state() or {}
    completed_features = state.get("completed_features", [])
    if feature_id in completed_features:
        return True

    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    user_story_ids = get_all_user_story_ids_in_feature(feature_id, release_plan) or []

    # Empty list means feature not found in release plan
    if not user_story_ids:
        return False

    completed_user_stories = state.get("completed_user_stories", [])
    all_user_stories_completed = all(
        user_story_id in completed_user_stories for user_story_id in user_story_ids
    )

    # Check ALL SCs for this feature from release plan, not just current_scs
    all_scs_ids = get_all_scs_ids_in_feature(feature_id, release_plan) or []
    all_scs_met = all(is_sc_met(sc_id, state) for sc_id in all_scs_ids)

    # Feature requires both user stories completed AND all SCs met
    if not all_scs_ids:
        return all_user_stories_completed
    return all_user_stories_completed and all_scs_met


def is_epic_completed(epic_id: str, state: dict | None = None) -> bool:
    if state is None:
        state = load_project_state() or {}
    completed_epics = state.get("completed_epics", [])
    if epic_id in completed_epics:
        return True
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    feature_ids = get_all_features_ids_in_epic(epic_id, release_plan) or []
    # Empty list means epic not found in release plan
    if not feature_ids:
        return False
    completed_features = state.get("completed_features", [])
    return all(feature_id in completed_features for feature_id in feature_ids)


def are_task_deps_completed(
    task_id: str, release_plan: dict, state: dict | None = None
) -> bool:
    """Check if task dependency is completed."""
    if state is None:
        state = load_project_state() or {}
    deps = get_task_dependencies_ids(task_id, release_plan) or []
    return all(is_task_completed(dep_id, state) for dep_id in deps)


def is_task_allowed(task_id: str, state: dict | None = None) -> bool:
    if state is None:
        state = load_project_state() or {}
    deps = get_current_task_dependencies(task_id, state) or []
    return all(is_task_completed(dep_id, state) for dep_id in deps)


# ---


# Finders


def find_tasks_allowed_in_user_story(
    user_story_id: str, state: dict | None = None
) -> list[str]:
    if state is None:
        state = load_project_state() or {}
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    tasks = get_all_tasks_ids_in_user_story(user_story_id, release_plan) or []
    return [task_id for task_id in tasks if is_task_allowed(task_id, state)]


# Resetters


def reset_all_tasks_status(state: dict | None = None) -> None:
    """Reset all tasks status in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_tasks"] = {
        task_id: "not_started" for task_id in state.get("current_tasks", {}).keys()
    }
    save_project_state(state)


def reset_all_acs_status(state: dict | None = None) -> None:
    """Reset all acceptance criteria status in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_acs"] = {
        ac_id: "unmet" for ac_id in state.get("current_acs", {}).keys()
    }
    save_project_state(state)


def reset_all_scs_status(state: dict | None = None) -> None:
    """Reset all success criteria status in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_scs"] = {
        sc_id: "unmet" for sc_id in state.get("current_scs", {}).keys()
    }
    save_project_state(state)


def reset_all_user_story_status(state: dict | None = None) -> None:
    """Reset all user story status in project state."""
    if state is None:
        state = load_project_state() or {}
    state["current_user_story_status"] = "not_started"
    save_project_state(state)


def refresh_current_tasks(state: dict | None = None) -> dict:
    """Refresh current_tasks with only the pending allowed tasks.

    Replaces current_tasks with tasks that:
    - Have dependencies met (allowed)
    - Are not yet completed

    Completed tasks are already recorded in completed_tasks list.
    """
    if state is None:
        state = load_project_state() or {}

    current_user_story_id = get_current_user_story(state)
    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}

    # Get ALL tasks in the user story
    all_tasks_ids = (
        get_all_tasks_ids_in_user_story(current_user_story_id, release_plan) or []
    )

    # Build new current_tasks with only pending allowed tasks
    new_current_tasks = {}
    for task_id in all_tasks_ids:
        if is_task_completed(task_id, state):
            continue  # Skip completed tasks
        if is_task_allowed(task_id, state):
            new_current_tasks[task_id] = "not_started"
            print(f"Task '{task_id}' is now available")

    state["current_tasks"] = new_current_tasks
    save_project_state(state)
    return new_current_tasks


# Utils


def increment_id(some_id: str) -> str:
    """Increment some id."""
    num = int(some_id[-3:]) + 1
    result = some_id[:-3] + str(num).zfill(3)
    return result


# Resolvers


def record_completed_task(task_id: str, state: dict | None = None) -> bool:
    """Record a completed task and unlock dependent tasks.

    After recording the task, refreshes current_tasks to include
    any tasks whose dependencies are now met.
    """
    if state is None:
        state = load_project_state() or {}
    current_completed_tasks = state.get("completed_tasks", [])

    if not is_task_completed(task_id, state):
        print(f"Task '{task_id}' is not completed")
        return False
    if task_id in current_completed_tasks:
        print(f"Task '{task_id}' is already completed")
        return False

    current_completed_tasks.append(task_id)
    set_completed_tasks(current_completed_tasks, state)

    # Refresh current_tasks to unlock dependent tasks
    state = load_project_state() or {}
    refresh_current_tasks(state)
    return True


def record_completed_user_story(user_story_id: str, state: dict | None = None) -> bool:
    """Resolve user story."""
    if state is None:
        state = load_project_state() or {}
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
    """Record completed feature in project state."""
    if state is None:
        state = load_project_state() or {}
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
    """Resolve completed epic."""
    if state is None:
        state = load_project_state() or {}
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
    """Resolve met acceptance criteria."""
    if state is None:
        state = load_project_state() or {}
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
    """Resolve met success criteria."""
    if state is None:
        state = load_project_state() or {}
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


def resolve_tasks(state: dict | None = None) -> bool:
    """Resolve completed tasks."""
    if state is None:
        state = load_project_state() or {}
    current_tasks_ids = get_current_tasks_ids(state) or []
    for task_id in current_tasks_ids:
        record_completed_task(task_id, state)
    return True


def resolve_completed_acs(state: dict | None = None) -> bool:
    """Resolve acceptance criteria."""
    if state is None:
        state = load_project_state() or {}
    current_acs_ids = get_current_acs_ids(state) or []
    for ac_id in current_acs_ids:
        record_met_ac(ac_id, state)
    return True


def resolve_completed_scs(state: dict | None = None) -> bool:
    """Resolve success criteria."""
    if state is None:
        state = load_project_state() or {}
    current_scs_ids = get_current_scs_ids(state) or []
    for sc_id in current_scs_ids:
        record_met_sc(sc_id, state)
    return True


def resolve_user_story(state: dict | None = None) -> bool:
    """Resolve user story with proper feature/epic hierarchy navigation."""
    resolve_tasks(state)
    state = load_project_state() or {}
    resolve_completed_acs(state)
    state = load_project_state() or {}
    resolve_completed_scs(state)
    state = load_project_state() or {}

    current_user_story_id = get_current_user_story(state)
    if not is_user_story_completed(current_user_story_id, state):
        print(f"User story '{current_user_story_id}' is not completed")
        return False

    record_completed_user_story(current_user_story_id, state)
    state = load_project_state() or {}

    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    current_feature_id = get_current_feature_id(state)
    current_epic_id = get_current_epic_id(state)

    # Check for next user story in SAME feature
    next_us_in_feature = get_next_user_story_id_in_feature(
        current_user_story_id, current_feature_id, release_plan
    )

    if next_us_in_feature:
        # Stay in same feature, move to next user story
        set_current_user_story(next_us_in_feature, state)
        state = load_project_state() or {}
        new_tasks = initialize_tasks(next_us_in_feature, release_plan, state)
        new_acs = initialize_acs(next_us_in_feature, release_plan)
        set_current_tasks(new_tasks, state)
        state = load_project_state() or {}
        set_current_acs(new_acs, state)
        # SCs stay the same since we're still in same feature
        print(
            f"Moved to next user story '{next_us_in_feature}' in feature '{current_feature_id}'"
        )
        return True

    # Last user story in feature - need to transition to next feature
    # First, mark current feature as completed if all conditions are met
    if is_feature_completed(current_feature_id, state):
        record_completed_feature(current_feature_id, state)
        state = load_project_state() or {}

    # Check for next feature in SAME epic
    next_feature_in_epic = get_next_feature_id_in_epic(
        current_feature_id, current_epic_id, release_plan
    )

    if next_feature_in_epic:
        # Move to next feature in same epic
        set_current_feature_id(next_feature_in_epic, state)
        state = load_project_state() or {}
        first_us = get_first_user_story_id_in_feature(
            next_feature_in_epic, release_plan
        )
        if first_us:
            set_current_user_story(first_us, state)
            state = load_project_state() or {}
            new_tasks = initialize_tasks(first_us, release_plan, state)
            new_acs = initialize_acs(first_us, release_plan)
            new_scs = initialize_scs(next_feature_in_epic, release_plan)
            set_current_tasks(new_tasks, state)
            state = load_project_state() or {}
            set_current_acs(new_acs, state)
            state = load_project_state() or {}
            set_current_scs(new_scs, state)
        print(
            f"Moved to next feature '{next_feature_in_epic}' in epic '{current_epic_id}'"
        )
        return True

    # Last feature in epic - need to transition to next epic
    if is_epic_completed(current_epic_id, state):
        record_completed_epic(current_epic_id, state)
        state = load_project_state() or {}

    next_epic = get_next_epic_id(current_epic_id, release_plan)
    if next_epic:
        set_current_epic_id(next_epic, state)
        state = load_project_state() or {}
        first_feature = get_first_feature_id_in_epic(next_epic, release_plan)
        if first_feature:
            set_current_feature_id(first_feature, state)
            state = load_project_state() or {}
            first_us = get_first_user_story_id_in_feature(first_feature, release_plan)
            if first_us:
                set_current_user_story(first_us, state)
                state = load_project_state() or {}
                new_tasks = initialize_tasks(first_us, release_plan, state)
                new_acs = initialize_acs(first_us, release_plan)
                new_scs = initialize_scs(first_feature, release_plan)
                set_current_tasks(new_tasks, state)
                state = load_project_state() or {}
                set_current_acs(new_acs, state)
                state = load_project_state() or {}
                set_current_scs(new_scs, state)
        print(f"Moved to next epic '{next_epic}'")
        return True

    # No more epics - release plan complete
    print("Release plan completed!")
    return True


def resolve_feature(state: dict | None = None) -> bool:
    """Resolve feature with proper epic hierarchy navigation."""
    if state is None:
        state = load_project_state() or {}
    resolve_user_story(state)
    state = load_project_state() or {}

    current_feature_id = get_current_feature_id(state)
    current_epic_id = get_current_epic_id(state)

    if not is_feature_completed(current_feature_id, state):
        print(f"Feature '{current_feature_id}' is not completed")
        return False

    record_completed_feature(current_feature_id, state)
    state = load_project_state() or {}

    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}

    # Check for next feature in SAME epic
    next_feature_in_epic = get_next_feature_id_in_epic(
        current_feature_id, current_epic_id, release_plan
    )

    if next_feature_in_epic:
        set_current_feature_id(next_feature_in_epic, state)
        state = load_project_state() or {}
        # Initialize first user story in new feature
        first_us = get_first_user_story_id_in_feature(
            next_feature_in_epic, release_plan
        )
        if first_us:
            set_current_user_story(first_us, state)
            state = load_project_state() or {}
            new_tasks = initialize_tasks(first_us, release_plan, state)
            new_acs = initialize_acs(first_us, release_plan)
            new_scs = initialize_scs(next_feature_in_epic, release_plan)
            set_current_tasks(new_tasks, state)
            state = load_project_state() or {}
            set_current_acs(new_acs, state)
            state = load_project_state() or {}
            set_current_scs(new_scs, state)
        print(f"Feature '{current_feature_id}' resolved to '{next_feature_in_epic}'")
        return True

    # Last feature in epic - check if epic is complete and move to next epic
    if is_epic_completed(current_epic_id, state):
        record_completed_epic(current_epic_id, state)
        state = load_project_state() or {}

    next_epic = get_next_epic_id(current_epic_id, release_plan)
    if next_epic:
        set_current_epic_id(next_epic, state)
        state = load_project_state() or {}
        first_feature = get_first_feature_id_in_epic(next_epic, release_plan)
        if first_feature:
            set_current_feature_id(first_feature, state)
            state = load_project_state() or {}
            first_us = get_first_user_story_id_in_feature(first_feature, release_plan)
            if first_us:
                set_current_user_story(first_us, state)
                state = load_project_state() or {}
                new_tasks = initialize_tasks(first_us, release_plan, state)
                new_acs = initialize_acs(first_us, release_plan)
                new_scs = initialize_scs(first_feature, release_plan)
                set_current_tasks(new_tasks, state)
                state = load_project_state() or {}
                set_current_acs(new_acs, state)
                state = load_project_state() or {}
                set_current_scs(new_scs, state)
        print(f"Feature '{current_feature_id}' resolved, moved to epic '{next_epic}'")
        return True

    print(f"Feature '{current_feature_id}' resolved. Release plan completed!")
    return True


def resolve_epic(state: dict | None = None) -> bool:
    """Resolve epic with proper hierarchy navigation."""
    if state is None:
        state = load_project_state() or {}
    resolve_feature(state)
    state = load_project_state() or {}

    current_epic_id = get_current_epic_id(state)
    if not is_epic_completed(current_epic_id, state):
        print(f"Epic '{current_epic_id}' is not completed")
        return False

    record_completed_epic(current_epic_id, state)
    state = load_project_state() or {}

    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    next_epic = get_next_epic_id(current_epic_id, release_plan)

    if next_epic:
        set_current_epic_id(next_epic, state)
        state = load_project_state() or {}
        # Initialize first feature in new epic
        first_feature = get_first_feature_id_in_epic(next_epic, release_plan)
        if first_feature:
            set_current_feature_id(first_feature, state)
            state = load_project_state() or {}
            first_us = get_first_user_story_id_in_feature(first_feature, release_plan)
            if first_us:
                set_current_user_story(first_us, state)
                state = load_project_state() or {}
                new_tasks = initialize_tasks(first_us, release_plan, state)
                new_acs = initialize_acs(first_us, release_plan)
                new_scs = initialize_scs(first_feature, release_plan)
                set_current_tasks(new_tasks, state)
                state = load_project_state() or {}
                set_current_acs(new_acs, state)
                state = load_project_state() or {}
                set_current_scs(new_scs, state)
        print(f"Epic '{current_epic_id}' resolved to '{next_epic}'")
        return True

    print(f"Epic '{current_epic_id}' resolved. Release plan completed!")
    return True


def resolve_state(state: dict | None = None) -> None:
    """Resolve project state."""
    if state is None:
        state = load_project_state() or {}

    resolve_epic(state)

    print(f"State resolved")


if __name__ == "__main__":
    state = load_project_state() or {}  # Reload after test_project_state saves
    # test_project_state()
    set_all_status_in_progress(state)
    set_all_status_completed(state)
    resolve_state(state)
