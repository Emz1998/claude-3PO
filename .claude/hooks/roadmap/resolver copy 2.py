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


def resolve_tasks(roadmap: dict | None = None) -> bool:
    if roadmap is None:
        roadmap = load_roadmap() or {}
    # Auto-resolve tasks - enforce dependencies and AC requirements.
    for phase in roadmap.get("phases", ""):
        for milestone in phase.get("milestones", ""):
            for task in milestone.get("tasks", ""):
                task_id = task.get("id", "")
                task_status = task.get("status", "")
                acs_met = are_all_acs_met_in_task(task_id, roadmap)
                if not acs_met and task_status == "completed":
                    set_task_status(task_id, "in_progress", roadmap)
                    continue
                elif acs_met and task_status != "completed":
                    set_task_status(task_id, "completed", roadmap)

    return True


def resolve_milestones(roadmap: dict | None = None) -> bool:
    # Auto-resolve milestones and phases based on their children's status.
    if roadmap is None:
        roadmap = load_roadmap() or {}
    for phase in roadmap.get("phases", []):
        for milestone in phase.get("milestones", []):
            milestone_id = milestone.get("id", "")
            all_tasks_completed = are_all_tasks_completed_in_milestone(
                milestone_id, roadmap
            )
            scs_met = are_all_scs_met_in_milestone(milestone_id, roadmap)
            milestone_status = milestone.get("status", "")
            if not scs_met and not all_tasks_completed:
                (
                    set_milestone_status(milestone_id, "in_progress", roadmap)
                    if milestone_status == "completed"
                    else None
                )
                continue
            elif scs_met and not all_tasks_completed:
                (
                    set_milestone_status(milestone_id, "completed", roadmap)
                    if milestone_status != "completed"
                    else None
                )
    return True


def resolve_phases(roadmap: dict | None = None) -> bool:
    if roadmap is None:
        roadmap = load_roadmap() or {}
    # Auto-resolve phases based on their children's status.
    for phase in roadmap.get("phases", ""):
        phase_id = phase.get("id", "")
        phase_status = phase.get("status", "")
        all_milestones_completed = are_all_milestones_completed_in_phase(phase_id)
        if all_milestones_completed and phase_status == "in_progress":
            set_phase_status(phase_id, "completed", roadmap)
        else:
            set_phase_status(phase_id, "in_progress", roadmap)
    return True


if __name__ == "__main__":
    roadmap_test = load_roadmap(ROADMAP_TEST_FILE_PATH) or {}
    resolve_tasks(roadmap_test)
