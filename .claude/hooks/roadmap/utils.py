#!/usr/bin/env python3
# Roadmap utilities for status loggers

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

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
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir)


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
    roadmap_path: Path | None = None,
) -> dict | None:
    """Load roadmap.json file."""
    if roadmap_path is None:
        roadmap_path = get_roadmap_path()
    if not roadmap_path.exists():
        return None

    try:
        with open(roadmap_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def get_current(
    query: Literal["task", "milestone", "phase"], roadmap: dict | None = load_roadmap()
) -> str | None:
    """Get current item from roadmap."""
    current = roadmap.get("current", {}) if roadmap else {}
    return current.get(query, "")


def get_phase(
    phase_id: str | None = get_current("phase"), roadmap: dict | None = load_roadmap()
) -> dict | None:
    """Find phase in roadmap by ID. Returns phase or None."""
    phases = roadmap.get("phases", []) if roadmap else []
    for phase in phases:
        if phase.get("id") == phase_id:
            return phase
    return None


def get_milestone(
    milestone_id: str | None = get_current("milestone"),
    roadmap: dict | None = load_roadmap(),
) -> dict | None:
    """Find milestone in roadmap. Returns (phase, milestone) or (None, None)."""
    phases = roadmap.get("phases", []) if roadmap else []
    for phase in phases:
        milestones = phase.get("milestones", [])
        for milestone in milestones:
            if milestone.get("id") == milestone_id:
                return milestone
    return None


def get_task(
    task_id: str | None = get_current("task"), roadmap: dict | None = load_roadmap()
) -> dict | None:
    """Find task in roadmap. Returns (phase, milestone, task) or (None, None, None)."""
    phases = roadmap.get("phases", []) if roadmap else []
    for phase in phases:
        milestones = phase.get("milestones", [])
        for milestone in milestones:
            tasks = milestone.get("tasks", [])
            for task in tasks:
                if task.get("id") == task_id:
                    return task
    return None


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


def save_roadmap(roadmap: dict, roadmap_path: Path | None = None) -> bool:
    # Save roadmap.json file with updated timestamp.
    if roadmap_path is None:
        roadmap_path = get_roadmap_path() or None
    try:
        roadmap["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        roadmap_path.write_text(json.dumps(roadmap, indent=2)) if roadmap_path else None
        return True
    except IOError:
        return False


def get_test_strategy(
    milestone_id: str = get_current("milestone") or "",
    roadmap: dict | None = load_roadmap(),
) -> str:
    milestone = get_milestone(milestone_id, roadmap)
    test_strategy = milestone.get("test_strategy", "TA") if milestone else ""
    return test_strategy


def get_all_completed_tasks(
    roadmap: dict | None = load_roadmap(),
) -> list[str]:
    if not roadmap:
        return []
    return [
        task["id"]
        for phase in roadmap.get("phases", [])
        for milestone in phase.get("milestones", [])
        for task in milestone.get("tasks", [])
        if task.get("status") == "completed"
    ]


def get_milestone_of_task(
    task_id: str = get_current("task") or "", roadmap: dict | None = load_roadmap()
) -> str | None:
    if not roadmap:
        return None
    return next(
        milestone["id"]
        for phase in roadmap.get("phases", [])
        for milestone in phase.get("milestones", [])
        for task in milestone.get("tasks", [])
        if task.get("id") == task_id
    )


def get_phase_of_milestone(
    milestone_id: str = get_current("milestone") or "",
    roadmap: dict | None = load_roadmap(),
) -> str | None:
    if not roadmap:
        return None
    return next(
        phase["id"]
        for phase in roadmap.get("phases", [])
        for milestone in phase.get("milestones", [])
        if milestone.get("id") == milestone_id
    )


# Validation functions


def is_milestone_completed(
    milestone_id: str = get_current("milestone") or "",
    roadmap: dict | None = load_roadmap(),
) -> bool:
    milestone = get_milestone(milestone_id, roadmap)
    return milestone.get("status") == "completed" if milestone else False


def is_task_completed(
    task_id: str = get_current("task") or "", roadmap: dict | None = load_roadmap()
) -> bool:
    task = get_task(task_id, roadmap)
    return task.get("status") == "completed" if task else False


def is_phase_completed(
    phase_id: str = get_current("phase") or "",
    roadmap: dict | None = load_roadmap(),
) -> bool:
    phase = get_phase(phase_id, roadmap)
    return phase.get("status") == "completed" if phase else False


def are_all_acs_met_in_task(
    task_id: str = get_current("task") or "",
    roadmap: dict | None = load_roadmap(),
) -> bool:
    task = get_task(task_id, roadmap)
    return (
        all(ac.get("status") == "met" for ac in task.get("acceptance_criteria", []))
        if task
        else False
    )


def are_all_scs_met_in_milestone(
    milestone_id: str = get_current("milestone") or "",
    roadmap: dict | None = load_roadmap(),
) -> bool:
    milestone = get_milestone(milestone_id, roadmap)
    return (
        all(sc.get("status") == "met" for sc in milestone.get("success_criteria", []))
        if milestone
        else False
    )


def are_all_tasks_completed_in_milestone(
    milestone_id: str = get_current("milestone") or "",
    roadmap: dict | None = load_roadmap(),
) -> bool:
    milestone = get_milestone(milestone_id, roadmap)
    return (
        all(task.get("status") == "completed" for task in milestone.get("tasks", []))
        if milestone
        else False
    )


def are_all_milestones_completed_in_phase(
    phase_id: str = get_current("phase") or "",
    roadmap: dict | None = load_roadmap(),
) -> bool:
    phase = get_phase(phase_id, roadmap)
    return (
        all(
            milestone.get("status") == "completed"
            for milestone in phase.get("milestones", [])
        )
        if phase
        else False
    )


def are_all_phases_completed(
    roadmap: dict | None = load_roadmap(),
) -> bool:
    return (
        all(phase.get("status") == "completed" for phase in roadmap.get("phases", []))
        if roadmap
        else False
    )


# if __name__ == "__main__":
#     roadmap_test = load_roadmap(ROADMAP_TEST_FILE_PATH)
#     print(are_all_milestones_completed_in_phase("PH-001", roadmap_test))
