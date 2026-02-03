#!/usr/bin/env python3
"""Core state persistence for release plan.

Provides file-locked load/save and project state initialization.
All getters, setters, checkers, and resolvers live in their own modules.
"""

import sys
from datetime import datetime
from pathlib import Path
from filelock import FileLock


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.json import load_json, save_json  # type: ignore


sys.path.insert(0, str(Path(__file__).parent.parent))
from release_plan.utils import (  # type: ignore
    load_release_plan,
    get_release_plan_path,
    PROJECT_ROOT,
)
from config.unified_loader import get_project_settings  # type: ignore


# Load project settings from unified configuration
_project_settings = get_project_settings()
PROJECT_STATE_FILE_PATH = PROJECT_ROOT / "project" / "state.json"
TARGET_RELEASE = _project_settings.target_release
PROJECT_NAME = _project_settings.name
CURRENT_VERSION = _project_settings.version

RELEASE_PLAN_PATH = get_release_plan_path("v0.1.0")
STATE_LOCK = FileLock(PROJECT_STATE_FILE_PATH.with_suffix(".lock"))


def load_project_state() -> dict:
    """Load project state from state.json with file locking."""
    with STATE_LOCK:
        return load_json(PROJECT_STATE_FILE_PATH)


def save_project_state(
    state: dict | None = None, file_path: Path | None = None
) -> bool:
    """Save project state to file with file locking."""
    if state is None:
        state = load_project_state() or {}
    if file_path is None:
        file_path = PROJECT_STATE_FILE_PATH
    file_path.parent.mkdir(parents=True, exist_ok=True)
    state["updated"] = datetime.now().isoformat()
    with STATE_LOCK:
        save_json(state, file_path)
    return True


def initialize_project_state() -> None:
    """Initialize project state with defaults from release plan."""
    from release_plan.resolvers import initialize_tasks, initialize_acs, initialize_scs  # type: ignore

    release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
    current_epic_id = "EPIC-001"
    current_feature_id = "FEAT-001"
    current_user_story_id = "US-001"
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
