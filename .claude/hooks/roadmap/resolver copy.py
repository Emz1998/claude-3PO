#!/usr/bin/env python3
"""Auto-resolver for roadmap with watchdog file watching."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent))
from roadmap.utils import (  # type: ignore
    are_all_acs_met_in_task,
    get_task,
    load_roadmap,
    get_milestone_of_task,
    are_all_scs_met_in_milestone,
    are_all_tasks_completed_in_milestone,
    get_milestone,
    get_phase_of_milestone,
    get_phase,
    are_all_milestones_completed_in_phase,
)
from roadmap.setters import set_task_status, set_milestone_status, set_phase_status  # type: ignore

StatusType = Literal["not_started", "in_progress", "completed"]
ROADMAP_TEST_FILE_PATH = Path("project/v0.1.0/release-plan/roadmap-test.json")


def resolve_tasks(task_id: str, roadmap: dict = load_roadmap() or {}) -> bool:
    # Auto-resolve tasks - enforce dependencies and AC requirements.
    task = get_task(task_id, roadmap)
    task_status = task.get("status") if task else None
    acs_met = are_all_acs_met_in_task(task_id, roadmap)

    if not acs_met and task_status == "completed":
        set_task_status(task_id, "in_progress", roadmap)
        return False
    set_task_status(task_id, "completed", roadmap)
    return True


def resolve_milestones(task_id: str, roadmap: dict = load_roadmap() or {}) -> bool:
    """Auto-resolve milestones and phases based on their children's status."""
    milestone_id = get_milestone_of_task(task_id, roadmap)
    print(f"Milestone ID: {milestone_id}")
    milestone = get_milestone(milestone_id, roadmap)
    milestone_status = milestone.get("status") if milestone else None
    if not milestone_id:
        return False
    scs_met = are_all_scs_met_in_milestone(milestone_id, roadmap)
    print(f"SCs met: {scs_met}")
    all_tasks_completed = are_all_tasks_completed_in_milestone(milestone_id, roadmap)
    print(f"All tasks completed: {all_tasks_completed}")
    print(not scs_met or not all_tasks_completed)
    if not scs_met or not all_tasks_completed:
        (
            set_milestone_status(milestone_id, "in_progress", roadmap)
            if milestone_status != "in_progress"
            else None
        )
        return False
    (
        set_milestone_status(milestone_id, "completed", roadmap)
        if milestone_status != "completed"
        else None
    )
    return True


def resolve_phases(task_id: str, roadmap: dict = load_roadmap() or {}) -> bool:
    """Auto-resolve phases based on their children's status."""
    milestone_id = get_milestone_of_task(task_id, roadmap) or ""
    print(f"Milestone ID: {milestone_id}")
    phase_id = get_phase_of_milestone(milestone_id, roadmap) or ""
    print(f"Phase ID: {phase_id}")
    phase = get_phase(phase_id, roadmap)
    phase_status = phase.get("status") if phase else None

    all_milestones_completed = are_all_milestones_completed_in_phase(phase_id, roadmap)
    print(f"All milestones completed: {all_milestones_completed}")
    if not all_milestones_completed:
        (
            set_phase_status(phase_id, "in_progress", roadmap)
            if phase_status != "in_progress"
            else None
        )
        return False
    (
        set_phase_status(phase_id, "completed", roadmap)
        if phase_status != "completed"
        else None
    )
    return True


if __name__ == "__main__":
    roadmap_test = load_roadmap(ROADMAP_TEST_FILE_PATH) or {}
    resolve_phases("T001", roadmap_test)
