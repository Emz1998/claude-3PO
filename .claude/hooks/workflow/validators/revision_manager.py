#!/usr/bin/env python3
"""Revision manager for creating and tracking revision tasks.

When criteria validation fails, creates revision tasks and saves them
to the project directory for tracking.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.json import load_json, save_json  # type: ignore

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent


def create_revision_tasks(
    failed_criteria: list[dict],
    criteria_type: Literal["ac_validation", "sc_validation", "epic_sc_validation"],
    round_num: int,
) -> list[dict]:
    """Create revision task entries from failed criteria.

    Args:
        failed_criteria: List of {"id": "AC-010", "description": "..."} dicts
        criteria_type: Type of validation that triggered revisions
        round_num: Revision round number

    Returns:
        List of revision task dicts
    """
    tasks = []
    for i, criteria in enumerate(failed_criteria, start=1):
        task_id = f"RT-{round_num}-{str(i).zfill(3)}"
        tasks.append({
            "id": task_id,
            "description": f"Fix: {criteria.get('description', criteria.get('id', ''))}",
            "source_criteria": criteria.get("id", ""),
            "status": "not_started",
            "created": datetime.now(timezone.utc).isoformat(),
        })
    return tasks


def _get_revisions_path(version: str, epic_id: str, feature_id: str) -> Path:
    """Get the path to the revision tasks JSON file."""
    return (
        PROJECT_ROOT
        / "project"
        / version
        / epic_id
        / feature_id
        / "revisions"
        / "revision_tasks.json"
    )


def save_revision_tasks(
    tasks: list[dict],
    version: str,
    epic_id: str,
    feature_id: str,
    criteria_type: str = "ac_validation",
    round_num: int = 1,
    failed_criteria: list[dict] | None = None,
) -> None:
    """Save revision tasks to the project directory.

    Creates directories if needed.
    """
    file_path = _get_revisions_path(version, epic_id, feature_id)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    revision_data = {
        "feature_id": feature_id,
        "created": datetime.now(timezone.utc).isoformat(),
        "revision_round": round_num,
        "trigger": criteria_type,
        "failed_criteria": failed_criteria or [],
        "revision_tasks": tasks,
    }

    save_json(revision_data, file_path)


def load_revision_tasks(version: str, epic_id: str, feature_id: str) -> dict:
    """Load revision tasks from the project directory.

    Returns:
        Revision data dict, or empty dict if not found
    """
    file_path = _get_revisions_path(version, epic_id, feature_id)
    if not file_path.exists():
        return {}
    return load_json(file_path) or {}


def inject_revision_tasks_into_state(
    revision_tasks: list[dict], state: dict
) -> dict:
    """Add RT-prefixed tasks into current_tasks in state.

    Args:
        revision_tasks: List of revision task dicts
        state: Current project state dict

    Returns:
        Updated state dict with revision tasks in current_tasks
    """
    current_tasks = state.get("current_tasks", {})
    for task in revision_tasks:
        task_id = task.get("id", "")
        if task_id and task_id not in current_tasks:
            current_tasks[task_id] = task.get("status", "not_started")

    state["current_tasks"] = current_tasks
    return state


def get_next_revision_round(version: str, epic_id: str, feature_id: str) -> int:
    """Get the next revision round number."""
    existing = load_revision_tasks(version, epic_id, feature_id)
    if not existing:
        return 1
    return existing.get("revision_round", 0) + 1
