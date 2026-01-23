#!/usr/bin/env python3
# Roadmap utilities for status loggers

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


# Type aliases for schema values
StatusType = Literal["not_started", "in_progress", "completed"]
CriteriaStatusType = Literal["met", "unmet"]
TestStrategyType = Literal["TDD", "TA"]


def get_project_dir() -> Path:
    """Get project directory from environment or cwd."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir)


def get_prd_path() -> Path:
    """Get the path to PRD.json."""
    project_dir = get_project_dir()
    return project_dir / "project" / "product" / "PRD.json"


def load_prd() -> dict | None:
    """Load PRD.json file."""
    prd_path = get_prd_path()
    if not prd_path.exists():
        return None

    try:
        with open(prd_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def get_current_version() -> str:
    """Retrieve current_version from PRD.json."""
    prd = load_prd()
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


def save_roadmap(roadmap_path: Path, roadmap: dict) -> bool:
    """Save roadmap.json file with updated timestamp."""
    try:
        roadmap["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(roadmap_path, "w") as f:
            json.dump(roadmap, f, indent=2)
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
