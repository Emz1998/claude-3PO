#!/usr/bin/env python3
"""Auto-resolver for roadmap statuses based on child item completion."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from roadmap.utils import load_roadmap, save_roadmap  # type: ignore

ROADMAP_TEST_FILE_PATH = Path("project/v0.1.0/release-plan/roadmap-test.json")


def _all_met(items: list[dict], status_value: str = "met") -> bool:
    """Check if all items have the specified status."""
    return bool(items) and all(item.get("status") == status_value for item in items)


def _all_completed(items: list[dict]) -> bool:
    """Check if all items are completed."""
    return _all_met(items, "completed")


def _any_in_progress(items: list[dict]) -> bool:
    """Check if any item is in progress or completed."""
    return any(item.get("status") in ("in_progress", "completed") for item in items)


def _resolve_status(
    items: list[dict], require_criteria: list[dict] | None = None
) -> str | None:
    """Determine status based on child items and optional criteria."""
    if not items:
        return None
    if _all_completed(items) and (
        require_criteria is None or _all_met(require_criteria)
    ):
        return "completed"
    if _any_in_progress(items):
        return "in_progress"
    return None


def _resolve_task(task: dict) -> None:
    """Resolve task status from acceptance criteria."""
    acs = task.get("acceptance_criteria", [])
    if _all_met(acs):
        task["status"] = "completed"


def _resolve_milestone(milestone: dict) -> None:
    """Resolve milestone status from tasks and success criteria."""
    for task in milestone.get("tasks", []):
        _resolve_task(task)

    tasks = milestone.get("tasks", [])
    scs = milestone.get("success_criteria", [])
    status = _resolve_status(tasks, scs)
    if status:
        milestone["status"] = status


def _resolve_phase(phase: dict) -> None:
    """Resolve phase status from milestones."""
    for milestone in phase.get("milestones", []):
        _resolve_milestone(milestone)

    milestones = phase.get("milestones", [])
    status = _resolve_status(milestones)
    if status:
        phase["status"] = status


def _get_current(items: list[dict]) -> dict | None:
    """Get the first non-completed item, or None if all are completed."""
    return next(
        (item for item in items if item.get("status", "") != "completed"),
        None,
    )


def _resolve_current(phases: list[dict]) -> dict:
    all_milestones = [m for p in phases for m in p.get("milestones", [])]
    all_tasks = [t for m in all_milestones for t in m.get("tasks", [])]

    phase = _get_current(phases)
    milestone = _get_current(all_milestones)
    task = _get_current(all_tasks)

    print(json.dumps(all_milestones, indent=2))

    return {
        "phase": phase.get("id", "") if phase else "",
        "milestone": milestone.get("id", "") if milestone else "",
        "task": task.get("id", "") if task else "",
    }


def resolve_roadmap(roadmap_path: Path | None = None) -> None:
    """Resolve all statuses in roadmap from bottom up."""
    roadmap = load_roadmap(roadmap_path) if roadmap_path else {}
    if not roadmap:
        return

    for phase in roadmap.get("phases", []):
        _resolve_phase(phase)

    phases = roadmap.get("phases", [])
    status = _resolve_status(phases)
    if status:
        roadmap["status"] = status

    save_roadmap(roadmap, roadmap_path)


if __name__ == "__main__":
    roadmap = load_roadmap(ROADMAP_TEST_FILE_PATH) or {}
    resolve_roadmap(ROADMAP_TEST_FILE_PATH)
    phases = roadmap.get("phases", [])
    # print(json.dumps(phases[0], indent=2))
    current = _resolve_current(phases)
    save_roadmap(roadmap, ROADMAP_TEST_FILE_PATH)
    print(json.dumps(current, indent=2))
