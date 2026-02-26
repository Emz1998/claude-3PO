#!/usr/bin/env python3
# Roadmap utilities for status loggers

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Tuple
from pprint import pprint

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.json import load_json  # type: ignore

# Type aliases for schema values
StatusType = Literal["not_started", "in_progress", "completed"]
CriteriaStatusType = Literal["met", "unmet"]
TestStrategyType = Literal["TDD", "TA"]


# Project root is 4 levels up from this file
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
PROJECT_STATUS_FILE_PATH = PROJECT_ROOT / "project" / "state.json"


def get_release_plan_path(version: str) -> Path:
    return (
        PROJECT_ROOT
        / "project"
        / version
        / "release-plan"
        / f"release-plan_{version}.json"
    )


def load_release_plan(
    release_plan_path: Path,
) -> dict | None:
    """Load roadmap.json file."""
    return load_json(release_plan_path)


def save_release_plan(roadmap: dict, roadmap_path: Path) -> bool:
    # Save roadmap.json file with updated timestamp.
    try:
        roadmap["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        roadmap_path.write_text(json.dumps(roadmap, indent=2)) if roadmap_path else None
        return True
    except IOError:
        return False


# Epics


def find_epic(
    epic_id: str,
    release_plan: dict | None = None,
) -> dict | None:
    """Find phase in roadmap by ID. Returns phase or None."""
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = release_plan.get("epics", [])
    return next((epic for epic in epics if epic.get("id") == epic_id), None)


def get_epics(release_plan: dict) -> list[dict] | None:
    return release_plan.get("epics", [])


# Features


def find_feature(
    feature_id: str,
    release_plan: dict | None = None,
) -> dict | None:
    """Find features in release plan. Returns features or None."""
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return next(
        (
            feature
            for epic in epics
            for feature in epic.get("features", [])
            if feature.get("id") == feature_id
        ),
        None,
    )


# User Stories


def find_user_story(
    user_story_id: str,
    release_plan: dict | None = None,
) -> dict | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return next(
        (
            user_story
            for epic in epics
            for feature in epic.get("features", "")
            for user_story in feature.get("user_stories", "")
            if user_story.get("id") == user_story_id
        ),
        None,
    )


# Tasks


def find_task(
    task_id: str,
    release_plan: dict | None = None,
) -> dict | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return next(
        (
            task
            for epic in epics
            for feature in epic.get("features", "")
            for user_story in feature.get("user_stories", [])
            for task in user_story.get("tasks", [])
            if task.get("id", "") == task_id
        ),
        None,
    )


# Acceptance Criteria
def find_acceptance_criteria(
    ac_id: str,
    release_plan: dict | None = None,
) -> dict | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return next(
        (
            ac
            for epic in epics
            for feature in epic.get("features", [])
            for user_story in feature.get("user_stories", [])
            for ac in user_story.get("acceptance_criteria", [])
            if ac.get("id", "") == ac_id
        ),
        None,
    )


# Success Criterias
def find_success_criteria(
    sc_id: str,
    release_plan: dict | None = None,
) -> dict | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return next(
        (
            sc
            for epic in epics
            for feature in epic.get("features", [])
            for sc in feature.get("success_criteria", [])
            if sc.get("id", "") == sc_id
        ),
        None,
    )


# Epic Success Criteria
def find_epic_success_criteria(
    esc_id: str,
    release_plan: dict | None = None,
) -> dict | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return next(
        (
            sc
            for epic in epics
            for sc in epic.get("success_criteria", [])
            if sc.get("id", "") == esc_id
        ),
        None,
    )


def get_all_epic_scs_ids(epic_id: str, release_plan: dict | None = None) -> list[str]:
    """Get all epic-level success criteria IDs for an epic."""
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epic = find_epic(epic_id, release_plan) or {}
    return [sc.get("id", "") for sc in epic.get("success_criteria", [])]


def find_feature_id_of_user_story(
    user_story_id: str, release_plan: dict | None = None
) -> str | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return next(
        (
            feature.get("id", "")
            for epic in epics
            for feature in epic.get("features", [])
            for user_story in feature.get("user_stories", [])
            if user_story.get("id", "") == user_story_id
        ),
        None,
    )


def find_epic_id_of_feature(
    feature_id: str, release_plan: dict | None = None
) -> str | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return next(
        (
            epic.get("id", "")
            for epic in epics
            for feature in epic.get("features", [])
            if feature.get("id", "") == feature_id
        ),
        None,
    )


def find_user_story_id_of_task(
    task_id: str, release_plan: dict | None = None
) -> str | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return next(
        (
            user_story.get("id", "")
            for epic in epics
            for feature in epic.get("features", [])
            for user_story in feature.get("user_stories", [])
            for task in user_story.get("tasks", [])
            if task.get("id", "") == task_id
        ),
        None,
    )


def find_all_tasks_in_user_story(
    user_story_id: str, release_plan: dict | None = None
) -> list[dict] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    user_story = find_user_story(user_story_id, release_plan) or {}
    return user_story.get("tasks", [])


def find_user_story_of_feature(
    feature_id: str, release_plan: dict | None = None
) -> str | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    feature = find_feature(feature_id, release_plan) or {}
    return feature.get("user_stories", [])


# ------------------- Getters -------------------

# Direct Getters


def get_feature_test_strategy(
    feature_id: str, release_plan: dict | None = None
) -> Literal["TDD", "TA"] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    feature = find_feature(feature_id, release_plan) or {}
    return feature.get("test_strategy", None)


def get_task_dependencies_ids(
    task_id: str, release_plan: dict | None = None
) -> list[str] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    task = find_task(task_id, release_plan) or {}
    return task.get("dependencies", [])


# Items Getters inside specific item type


def get_all_features_in_epic(
    epic_id: str, release_plan: dict | None = None
) -> list[dict] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epic = find_epic(epic_id, release_plan) or {}
    return epic.get("features", [])


def get_all_user_stories_in_feature(
    feature_id: str, release_plan: dict | None = None
) -> list[dict] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    feature = find_feature(feature_id, release_plan) or {}
    return feature.get("user_stories", [])


def get_all_acs_in_user_story(
    user_story_id: str, release_plan: dict | None = None
) -> list[dict] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    user_story = find_user_story(user_story_id, release_plan) or {}
    return user_story.get("acceptance_criteria", [])


def get_all_scs_in_feature(
    feature_id: str, release_plan: dict | None = None
) -> list[dict] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    feature = find_feature(feature_id, release_plan) or {}
    return feature.get("success_criteria", [])


# Getters that only return the tasks, scs, and acs themselves in order.


def get_all_features_only(release_plan: dict | None = None) -> list[dict] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return [feature for epic in epics for feature in epic.get("features", [])]


def get_all_user_stories_only(release_plan: dict | None = None) -> list[dict] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return [
        user_story
        for epic in epics
        for feature in epic.get("features", [])
        for user_story in feature.get("user_stories", [])
    ]


def get_all_tasks_only(release_plan: dict | None = None) -> list[dict] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return [
        task
        for epic in epics
        for feature in epic.get("features", [])
        for user_story in feature.get("user_stories", [])
        for task in user_story.get("tasks", [])
    ]


def get_all_scs_only(release_plan: dict | None = None) -> list[dict] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return [
        sc
        for epic in epics
        for feature in epic.get("features", [])
        for sc in feature.get("success_criteria", [])
    ]


def get_all_acs_only(release_plan: dict | None = None) -> list[dict] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return [
        ac
        for epic in epics
        for feature in epic.get("features", [])
        for user_story in feature.get("user_stories", [])
        for ac in user_story.get("acceptance_criteria", [])
    ]


# All IDs Getters with one item type only.


def get_all_tasks_ids(release_plan: dict | None = None) -> list[str] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    return [task.get("id", "") for task in get_all_tasks_only(release_plan) or []]


def get_all_scs_ids(release_plan: dict | None = None) -> list[str] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    return [sc.get("id", "") for sc in get_all_scs_only(release_plan) or []]


def get_all_features_ids(release_plan: dict | None = None) -> list[str] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    return [
        feature.get("id", "") for feature in get_all_features_only(release_plan) or []
    ]


def get_all_user_stories_ids(release_plan: dict | None = None) -> list[str] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    return [
        user_story.get("id", "")
        for user_story in get_all_user_stories_only(release_plan) or []
    ]


# IDs Getters inside specific item type


def get_all_features_ids_in_epic(
    epic_id: str, release_plan: dict | None = None
) -> list[str] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    return [
        feature.get("id", "")
        for feature in get_all_features_in_epic(epic_id, release_plan) or []
    ]


def get_all_tasks_ids_in_user_story(
    user_story_id: str, release_plan: dict | None = None
) -> list[str] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    return [
        task.get("id", "")
        for task in find_all_tasks_in_user_story(user_story_id, release_plan) or []
    ]


def get_all_scs_ids_in_feature(
    feature_id: str, release_plan: dict | None = None
) -> list[str] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    feature = find_feature(feature_id, release_plan) or {}
    return [sc.get("id", "") for sc in feature.get("success_criteria", []) or []]


def get_all_acs_ids_in_user_story(
    user_story_id: str, release_plan: dict | None = None
) -> list[str] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    user_story = find_user_story(user_story_id, release_plan) or {}
    return [ac.get("id", "") for ac in user_story.get("acceptance_criteria", []) or []]


def get_all_user_story_ids_in_feature(
    feature_id: str, release_plan: dict | None = None
) -> list[str] | None:
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    feature = find_feature(feature_id, release_plan) or {}
    return [
        user_story.get("id", "") for user_story in feature.get("user_stories", []) or []
    ]


# ------------------- Hierarchy Navigation -------------------


def get_all_epic_ids(release_plan: dict | None = None) -> list[str]:
    """Get all epic IDs in order from the release plan."""
    if not release_plan:
        release_plan = load_release_plan(get_release_plan_path("v0.1.0")) or {}
    epics = get_epics(release_plan) or []
    return [epic.get("id", "") for epic in epics]


def get_first_epic_id(release_plan: dict | None = None) -> str | None:
    """Get the first epic ID in the release plan."""
    epic_ids = get_all_epic_ids(release_plan)
    return epic_ids[0] if epic_ids else None


def get_next_epic_id(
    current_epic_id: str, release_plan: dict | None = None
) -> str | None:
    """Get the next epic ID after current, or None if last epic."""
    epic_ids = get_all_epic_ids(release_plan)
    if current_epic_id not in epic_ids:
        return None
    current_index = epic_ids.index(current_epic_id)
    if current_index + 1 < len(epic_ids):
        return epic_ids[current_index + 1]
    return None


def get_first_feature_id_in_epic(
    epic_id: str, release_plan: dict | None = None
) -> str | None:
    """Get the first feature ID in an epic."""
    feature_ids = get_all_features_ids_in_epic(epic_id, release_plan) or []
    return feature_ids[0] if feature_ids else None


def get_next_feature_id_in_epic(
    current_feature_id: str, epic_id: str, release_plan: dict | None = None
) -> str | None:
    """Get the next feature ID within the same epic, or None if last feature."""
    feature_ids = get_all_features_ids_in_epic(epic_id, release_plan) or []
    if current_feature_id not in feature_ids:
        return None
    current_index = feature_ids.index(current_feature_id)
    if current_index + 1 < len(feature_ids):
        return feature_ids[current_index + 1]
    return None


def get_first_user_story_id_in_feature(
    feature_id: str, release_plan: dict | None = None
) -> str | None:
    """Get the first user story ID in a feature."""
    user_story_ids = get_all_user_story_ids_in_feature(feature_id, release_plan) or []
    return user_story_ids[0] if user_story_ids else None


def get_next_user_story_id_in_feature(
    current_user_story_id: str, feature_id: str, release_plan: dict | None = None
) -> str | None:
    """Get the next user story ID within the same feature, or None if last."""
    user_story_ids = get_all_user_story_ids_in_feature(feature_id, release_plan) or []
    if current_user_story_id not in user_story_ids:
        return None
    current_index = user_story_ids.index(current_user_story_id)
    if current_index + 1 < len(user_story_ids):
        return user_story_ids[current_index + 1]
    return None


# if __name__ == "__main__":
#     release_plan_path = get_release_plan_path("v0.1.0")
#     release_plan = load_release_plan(release_plan_path) or {}
#     pprint(get_all_tasks(release_plan))
