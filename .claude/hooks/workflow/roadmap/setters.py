#!/usr/bin/env python3
# Roadmap utilities for status loggers

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from flatten_dict import flatten, unflatten  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.json import load_json  # type: ignore

# Type aliases for schema values
StatusType = Literal["not_started", "in_progress", "completed"]
CriteriaStatusType = Literal["met", "unmet"]
TestStrategyType = Literal["TDD", "TA"]


PROJECT_STATUS_FILE_PATH = Path("project/status.json")
ROADMAP_TEST_FILE_PATH = Path("project/v0.1.0/release-plan/roadmap-test.json")


def get_project_dir() -> Path:
    """Get project directory from environment or cwd."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(project_dir) if project_dir else Path.cwd()


def get_current_version() -> str:
    """Retrieve current_version from PRD.json."""
    prd = load_json(str(PROJECT_STATUS_FILE_PATH))
    if prd is None:
        return ""
    return prd.get("current_version", "")


def get_roadmap_path(version: str = get_current_version()) -> Path:
    """Get roadmap.json path for the given version."""
    project_dir = get_project_dir()
    return project_dir / "project" / version / "release-plan" / "roadmap.json"


def load_roadmap(
    roadmap_path: Path = get_roadmap_path(),
) -> dict | None:
    """Load roadmap.json file."""
    if not roadmap_path.exists():
        return None

    try:
        return json.loads(roadmap_path.read_text())
    except (json.JSONDecodeError, IOError):
        return None


def save_roadmap(roadmap: dict, roadmap_path: Path = get_roadmap_path()) -> bool:
    """Save roadmap.json file with updated timestamp."""
    try:
        roadmap["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        roadmap_path.write_text(json.dumps(roadmap, indent=2))
        return True
    except IOError:
        return False


def set_current(
    query: Literal["task", "milestone", "phase"],
    value: str,
    roadmap: dict = load_roadmap() or {},
) -> bool:
    """Set current item in roadmap."""
    roadmap["current"][query] = value
    return save_roadmap(roadmap)


def set_phases(
    phases: list[dict],
    roadmap: dict = load_roadmap() or {},
) -> bool:
    flattened_phases = flatten(phases)
    roadmap["phases"] = phases
    return save_roadmap(roadmap)


def set_milestones(
    phase_id: str,
    milestones: list[dict],
    roadmap: dict = load_roadmap() or {},
) -> bool:
    """Set milestones in roadmap."""
    roadmap["phases"][phase_id]["milestones"] = milestones
    return save_roadmap(roadmap)


def set_task(
    task_id: str,
    phase_id: str,
    task: dict,
    roadmap: dict = load_roadmap() or {},
) -> bool:
    """Set task in roadmap."""
    roadmap["phases"][phase_id]["tasks"][task_id] = task
    return save_roadmap(roadmap)


def get_ac(
    ac_id: str, roadmap: dict | None = load_roadmap()
) -> tuple[dict | None, dict | None]:
    """Find acceptance criteria in roadmap. Returns (task, ac_entry) or (None, None)."""
    phases = roadmap.get("phases", []) if roadmap else []
    for phase in phases:
        milestones = phase.get("milestones", [])
        for milestone in milestones:
            tasks = milestone.get("tasks", [])
            for task in tasks:
                acceptance_criteria = task.get("acceptance_criteria", [])
                for ac in acceptance_criteria:
                    id = ac.get("id", "")
                    if ac_id == id:
                        return task, ac
    return None, None


def get_sc(
    sc_id: str, roadmap: dict | None = load_roadmap()
) -> tuple[dict | None, dict | None]:
    """Find success criteria in roadmap. Returns (milestone, sc_entry) or (None, None)."""
    phases = roadmap.get("phases", []) if roadmap else []
    for phase in phases:
        milestones = phase.get("milestones", [])
        for milestone in milestones:
            success_criteria = milestone.get("success_criteria", [])
            for sc in success_criteria:
                id = sc.get("id", "")
                if sc_id == id:
                    return milestone, sc
    return None, None


def set_task_status(
    task_id: str,
    status: StatusType,
    roadmap: dict | None = load_roadmap(),
) -> bool:
    if not roadmap:
        return False
    for phase in roadmap.get("phases", []):
        for milestone in phase.get("milestones", []):
            for task in milestone.get("tasks", []):
                if task.get("id") == task_id:
                    task["status"] = status
                    save_roadmap(roadmap, ROADMAP_TEST_FILE_PATH)
                    return True
    return False


def set_milestone_status(
    milestone_id: str,
    status: StatusType,
    roadmap: dict | None = load_roadmap(),
) -> bool:
    """Set milestone status in roadmap."""
    if not roadmap:
        return False
    for phase in roadmap.get("phases", []):
        for milestone in phase.get("milestones", []):
            if milestone.get("id") == milestone_id:
                milestone["status"] = status
                return save_roadmap(roadmap, ROADMAP_TEST_FILE_PATH)
    return False


def set_phase_status(
    phase_id: str,
    status: StatusType,
    roadmap: dict | None = load_roadmap(),
) -> bool:
    """Set phase status in roadmap."""
    if not roadmap:
        return False
    for phase in roadmap.get("phases", []):
        if phase.get("id") == phase_id:
            phase["status"] = status
            return save_roadmap(roadmap, ROADMAP_TEST_FILE_PATH)
    return False


if __name__ == "__main__":
    roadmap_test = load_roadmap(ROADMAP_TEST_FILE_PATH)
    set_milestone_status("MS-001", "completed", roadmap_test)
