#!/usr/bin/env python3
# Roadmap Status Update Script - Updates task, SC, or AC status in roadmap.json

import argparse
import json
import os
import sys
import re
from datetime import datetime, timezone
from pathlib import Path


TASK_STATUSES = ["not_started", "in_progress", "completed", "blocked"]
CRITERIA_STATUSES = ["met", "unmet"]

TASK_PATTERN = r"^T\d{3}$"
AC_PATTERN = r"^AC-\d{3}$"
SC_PATTERN = r"^SC-\d{3}$"


def get_project_dir() -> Path:
    """Get project directory from environment or cwd."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir)


def load_prd() -> dict | None:
    """Load PRD.json file."""
    prd_path = get_project_dir() / "project" / "product" / "PRD.json"
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


def get_roadmap_path(version: str) -> Path:
    """Get roadmap.json path for the given version."""
    return get_project_dir() / "project" / version / "release-plan" / "roadmap.json"


def load_roadmap(roadmap_path: Path) -> dict | None:
    """Load roadmap.json file."""
    if not roadmap_path.exists():
        return None
    try:
        with open(roadmap_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_roadmap(roadmap_path: Path, roadmap: dict) -> bool:
    """Save roadmap.json file with updated timestamp."""
    try:
        roadmap["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(roadmap_path, "w") as f:
            json.dump(roadmap, f, indent=2)
        return True
    except IOError:
        return False


def find_task_in_roadmap(
    roadmap: dict, task_id: str
) -> tuple[dict | None, dict | None, dict | None]:
    """Find task in roadmap. Returns (phase, milestone, task) or (None, None, None)."""
    phases = roadmap.get("phases", [])
    for phase in phases:
        milestones = phase.get("milestones", [])
        for milestone in milestones:
            tasks = milestone.get("tasks", [])
            for task in tasks:
                if task.get("id") == task_id:
                    return phase, milestone, task
    return None, None, None


def find_ac_in_roadmap(roadmap: dict, ac_id: str) -> tuple[dict | None, dict | None]:
    """Find acceptance criteria in roadmap. Returns (task, ac_entry) or (None, None)."""
    phases = roadmap.get("phases", [])
    for phase in phases:
        milestones = phase.get("milestones", [])
        for milestone in milestones:
            tasks = milestone.get("tasks", [])
            for task in tasks:
                acceptance_criteria = task.get("acceptance_criteria", [])
                for ac in acceptance_criteria:
                    if ac_id == ac.get("id", ""):
                        return task, ac
    return None, None


def find_sc_in_roadmap(roadmap: dict, sc_id: str) -> tuple[dict | None, dict | None]:
    """Find success criteria in roadmap. Returns (milestone, sc_entry) or (None, None)."""
    phases = roadmap.get("phases", [])
    for phase in phases:
        milestones = phase.get("milestones", [])
        for milestone in milestones:
            success_criteria = milestone.get("success_criteria", [])
            for sc in success_criteria:
                if sc_id == sc.get("id", ""):
                    return milestone, sc
    return None, None


def find_milestone_in_roadmap(
    roadmap: dict, milestone_id: str
) -> tuple[dict | None, dict | None]:
    """Find milestone in roadmap. Returns (phase, milestone) or (None, None)."""
    phases = roadmap.get("phases", [])
    for phase in phases:
        milestones = phase.get("milestones", [])
        for milestone in milestones:
            if milestone.get("id") == milestone_id:
                return phase, milestone
    return None, None


def get_incomplete_task_deps(roadmap: dict, task: dict) -> list[str]:
    """Get list of incomplete dependency IDs for a task."""
    incomplete = []
    for dep_id in task.get("dependencies", []):
        _, _, dep_task = find_task_in_roadmap(roadmap, dep_id)
        if dep_task and dep_task.get("status") != "completed":
            incomplete.append(dep_id)
    return incomplete


def get_incomplete_milestone_deps(roadmap: dict, milestone: dict) -> list[str]:
    """Get list of incomplete dependency IDs for a milestone."""
    incomplete = []
    for dep_id in milestone.get("dependencies", []):
        _, dep_milestone = find_milestone_in_roadmap(roadmap, dep_id)
        if dep_milestone and dep_milestone.get("status") != "completed":
            incomplete.append(dep_id)
    return incomplete


def get_unmet_acs(task: dict) -> list[str]:
    """Get list of unmet acceptance criteria IDs for a task."""
    unmet = []
    for ac in task.get("acceptance_criteria", []):
        if ac.get("status") != "met":
            unmet.append(ac.get("id", "unknown"))
    return unmet


def get_unmet_scs(milestone: dict) -> list[str]:
    """Get list of unmet success criteria IDs for a milestone."""
    unmet = []
    for sc in milestone.get("success_criteria", []):
        if sc.get("status") != "met":
            unmet.append(sc.get("id", "unknown"))
    return unmet


def all_acs_met(task: dict) -> bool:
    """Check if all acceptance criteria for a task are met."""
    acs = task.get("acceptance_criteria", [])
    if not acs:
        return True
    return all(ac.get("status") == "met" for ac in acs)


def all_scs_met(milestone: dict) -> bool:
    """Check if all success criteria for a milestone are met."""
    scs = milestone.get("success_criteria", [])
    if not scs:
        return True
    return all(sc.get("status") == "met" for sc in scs)


def all_tasks_completed(milestone: dict) -> bool:
    """Check if all tasks in a milestone are completed."""
    tasks = milestone.get("tasks", [])
    if not tasks:
        return False
    return all(task.get("status") == "completed" for task in tasks)


def any_task_in_progress(milestone: dict) -> bool:
    """Check if any task in a milestone is in_progress."""
    tasks = milestone.get("tasks", [])
    return any(task.get("status") == "in_progress" for task in tasks)


def all_milestones_completed(phase: dict) -> bool:
    """Check if all milestones in a phase are completed."""
    milestones = phase.get("milestones", [])
    if not milestones:
        return False
    return all(ms.get("status") == "completed" for ms in milestones)


def any_milestone_in_progress(phase: dict) -> bool:
    """Check if any milestone in a phase is in_progress."""
    milestones = phase.get("milestones", [])
    return any(ms.get("status") == "in_progress" for ms in milestones)


def resolve_project_status(roadmap: dict) -> str | None:
    """Auto-resolve project status based on phases."""
    phases = roadmap.get("phases", [])
    current_status = roadmap.get("status", "not_started")

    all_completed = all(p.get("status") == "completed" for p in phases) if phases else False
    any_in_progress = any(p.get("status") == "in_progress" for p in phases)

    if current_status != "completed" and all_completed:
        roadmap["status"] = "completed"
        return "Project status auto-resolved to 'completed'"
    elif current_status in ("not_started", "pending") and any_in_progress:
        roadmap["status"] = "in_progress"
        return "Project status auto-resolved to 'in_progress'"
    elif current_status == "completed" and not all_completed:
        roadmap["status"] = "in_progress"
        return "Project status reverted to 'in_progress'"
    return None


def resolve_milestones_and_phases(roadmap: dict) -> list[str]:
    """Auto-resolve milestones and phases based on their children's status."""
    resolutions = []
    phases = roadmap.get("phases", [])

    for phase in phases:
        milestones = phase.get("milestones", [])

        for milestone in milestones:
            current_status = milestone.get("status")
            tasks_completed = all_tasks_completed(milestone)
            scs_met = all_scs_met(milestone)
            has_task_in_progress = any_task_in_progress(milestone)

            # Auto-progress: pending -> in_progress when task starts
            if current_status in ("pending", "not_started") and has_task_in_progress:
                milestone["status"] = "in_progress"
                resolutions.append(
                    f"Milestone '{milestone.get('id')}' auto-progressed to 'in_progress'"
                )
            # Auto-complete when all tasks done
            elif current_status != "completed" and tasks_completed:
                if not scs_met:
                    unmet = get_unmet_scs(milestone)
                    resolutions.append(
                        f"Milestone '{milestone.get('id')}' cannot be completed. "
                        f"Unmet success criteria: {', '.join(unmet)}"
                    )
                else:
                    milestone["status"] = "completed"
                    resolutions.append(
                        f"Milestone '{milestone.get('id')}' auto-resolved to 'completed'"
                    )
            # Revert if completed but tasks not done
            elif current_status == "completed" and not tasks_completed:
                milestone["status"] = "in_progress"
                resolutions.append(
                    f"Milestone '{milestone.get('id')}' reverted to 'in_progress'"
                )

        current_phase_status = phase.get("status")
        milestones_completed = all_milestones_completed(phase)
        has_milestone_in_progress = any_milestone_in_progress(phase)

        # Auto-progress: pending -> in_progress when milestone starts
        if current_phase_status in ("pending", "not_started") and has_milestone_in_progress:
            phase["status"] = "in_progress"
            resolutions.append(
                f"Phase '{phase.get('id')}' auto-progressed to 'in_progress'"
            )
        # Auto-complete when all milestones done
        elif current_phase_status != "completed" and milestones_completed:
            phase["status"] = "completed"
            resolutions.append(
                f"Phase '{phase.get('id')}' auto-resolved to 'completed'"
            )
        # Revert if completed but milestones not done
        elif current_phase_status == "completed" and not milestones_completed:
            phase["status"] = "in_progress"
            resolutions.append(f"Phase '{phase.get('id')}' reverted to 'in_progress'")

    return resolutions


def update_current_pointer(roadmap: dict) -> str | None:
    """Update the 'current' section to point to the next pending task."""
    phases = roadmap.get("phases", [])
    current = roadmap.get("current", {})
    old_current = (current.get("phase"), current.get("milestone"), current.get("task"))

    new_phase_id = None
    new_milestone_id = None
    new_task_id = None

    for phase in phases:
        if phase.get("status") == "completed":
            continue

        new_phase_id = phase.get("id")
        milestones = phase.get("milestones", [])

        for milestone in milestones:
            if milestone.get("status") == "completed":
                continue

            new_milestone_id = milestone.get("id")
            tasks = milestone.get("tasks", [])

            for task in tasks:
                if task.get("status") == "completed":
                    continue

                new_task_id = task.get("id")
                break

            if new_task_id:
                break

        if new_milestone_id:
            break

    if not new_phase_id and phases:
        last_phase = phases[-1]
        new_phase_id = last_phase.get("id")
        milestones = last_phase.get("milestones", [])
        if milestones:
            last_milestone = milestones[-1]
            new_milestone_id = last_milestone.get("id")
            tasks = last_milestone.get("tasks", [])
            if tasks:
                new_task_id = tasks[-1].get("id")

    new_current = (new_phase_id, new_milestone_id, new_task_id)

    if new_current != old_current:
        roadmap["current"] = {
            "phase": new_phase_id,
            "milestone": new_milestone_id,
            "task": new_task_id,
        }
        return f"Current updated: phase={new_phase_id}, milestone={new_milestone_id}, task={new_task_id}"

    return None


def update_summary(roadmap: dict) -> None:
    """Update the summary section with current counts."""
    phases = roadmap.get("phases", [])
    summary = roadmap.get("summary", {})

    phase_total = len(phases)
    phase_completed = sum(1 for p in phases if p.get("status") == "completed")

    milestone_total = 0
    milestone_completed = 0
    task_total = 0
    task_completed = 0

    for phase in phases:
        milestones = phase.get("milestones", [])
        milestone_total += len(milestones)
        milestone_completed += sum(
            1 for m in milestones if m.get("status") == "completed"
        )

        for milestone in milestones:
            tasks = milestone.get("tasks", [])
            task_total += len(tasks)
            task_completed += sum(1 for t in tasks if t.get("status") == "completed")

    summary["phases"] = {
        "total": phase_total,
        "pending": phase_total - phase_completed,
        "completed": phase_completed,
    }
    summary["milestones"] = {
        "total": milestone_total,
        "pending": milestone_total - milestone_completed,
        "completed": milestone_completed,
    }
    summary["tasks"] = {
        "total": task_total,
        "pending": task_total - task_completed,
        "completed": task_completed,
    }

    roadmap["summary"] = summary


def run_auto_resolver(version: str) -> tuple[bool, list[str]]:
    """Run the auto-resolver for milestones, phases, and project status."""
    roadmap_path = get_roadmap_path(version)
    roadmap = load_roadmap(roadmap_path)
    if roadmap is None:
        return False, [f"Could not load roadmap from: {roadmap_path}"]

    resolutions = resolve_milestones_and_phases(roadmap)

    project_msg = resolve_project_status(roadmap)
    if project_msg:
        resolutions.append(project_msg)

    current_msg = update_current_pointer(roadmap)
    if current_msg:
        resolutions.append(current_msg)

    update_summary(roadmap)
    if not save_roadmap(roadmap_path, roadmap):
        return False, ["Failed to save roadmap after auto-resolution"]

    return True, resolutions


def detect_item_type(item_id: str) -> str | None:
    """Detect the type of item based on its ID pattern."""
    if re.match(TASK_PATTERN, item_id):
        return "task"
    elif re.match(AC_PATTERN, item_id):
        return "ac"
    elif re.match(SC_PATTERN, item_id):
        return "sc"
    return None


def get_valid_statuses(item_type: str) -> list[str]:
    """Get valid statuses for the item type."""
    if item_type == "task":
        return TASK_STATUSES
    return CRITERIA_STATUSES


def update_task(roadmap: dict, task_id: str, status: str) -> tuple[bool, str]:
    """Update task status with validation."""
    _phase, milestone, task = find_task_in_roadmap(roadmap, task_id)
    if task is None or milestone is None:
        return False, f"Task '{task_id}' not found in roadmap"

    # Check dependencies before allowing in_progress or completed
    if status in ("in_progress", "completed"):
        incomplete_ms_deps = get_incomplete_milestone_deps(roadmap, milestone)
        if incomplete_ms_deps:
            action = "start" if status == "in_progress" else "complete"
            return False, (
                f"Cannot {action} task '{task_id}'. "
                f"Milestone '{milestone.get('id')}' has incomplete dependencies: "
                f"{', '.join(incomplete_ms_deps)}. Complete them first."
            )
        incomplete_task_deps = get_incomplete_task_deps(roadmap, task)
        if incomplete_task_deps:
            action = "start" if status == "in_progress" else "complete"
            return False, (
                f"Cannot {action} task '{task_id}'. "
                f"Incomplete task dependencies: {', '.join(incomplete_task_deps)}. "
                f"Complete them first."
            )

    # Check ACs before allowing completed
    if status == "completed" and not all_acs_met(task):
        unmet = get_unmet_acs(task)
        return False, (
            f"Cannot mark task '{task_id}' as completed. "
            f"Unmet acceptance criteria: {', '.join(unmet)}. "
            f"Mark all ACs as 'met' first."
        )

    task["status"] = status
    return True, f"Task '{task_id}' status updated to '{status}'"


def update_ac(roadmap: dict, ac_id: str, status: str) -> tuple[bool, str]:
    """Update acceptance criteria status."""
    task, ac = find_ac_in_roadmap(roadmap, ac_id)
    if ac is None:
        return False, f"Acceptance criteria '{ac_id}' not found in roadmap"
    # Block AC logging if task is not in_progress
    task_status = task.get("status", "not_started") if task else "not_started"
    if task_status != "in_progress":
        return False, (
            f"Cannot update AC '{ac_id}'. "
            f"Task '{task.get('id')}' must be 'in_progress' first (current: '{task_status}')."
        )
    ac["status"] = status
    return True, f"Acceptance criteria '{ac_id}' status updated to '{status}'"


def update_sc(roadmap: dict, sc_id: str, status: str) -> tuple[bool, str]:
    """Update success criteria status."""
    milestone, sc = find_sc_in_roadmap(roadmap, sc_id)
    if sc is None:
        return False, f"Success criteria '{sc_id}' not found in roadmap"
    # Block SC logging if not all tasks in milestone are completed
    if milestone and not all_tasks_completed(milestone):
        incomplete_tasks = [
            t.get("id") for t in milestone.get("tasks", [])
            if t.get("status") != "completed"
        ]
        return False, (
            f"Cannot update SC '{sc_id}'. "
            f"All tasks in milestone '{milestone.get('id')}' must be completed first. "
            f"Incomplete: {', '.join(incomplete_tasks)}."
        )
    sc["status"] = status
    return True, f"Success criteria '{sc_id}' status updated to '{status}'"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update task, AC, or SC status in roadmap.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s T001 in_progress   # Start working on task T001
  %(prog)s T002 completed     # Mark task T002 as completed
  %(prog)s T003 blocked       # Mark task T003 as blocked
  %(prog)s T001 not_started   # Reset task T001 to not started
  %(prog)s AC-001 met         # Mark acceptance criteria AC-001 as met
  %(prog)s AC-002 unmet       # Mark acceptance criteria AC-002 as unmet
  %(prog)s SC-001 met         # Mark success criteria SC-001 as met
  %(prog)s SC-002 unmet       # Mark success criteria SC-002 as unmet

Item ID formats:
  Task:               TXXX (e.g., T001, T002)
  Acceptance Criteria: AC-XXX (e.g., AC-001, AC-002)
  Success Criteria:    SC-XXX (e.g., SC-001, SC-002)

Valid statuses:
  Task:    not_started, in_progress, completed, blocked
  AC/SC:   met, unmet
        """
    )
    parser.add_argument(
        "item_id",
        type=str,
        help="Item ID (TXXX for task, AC-XXX for acceptance criteria, SC-XXX for success criteria)"
    )
    parser.add_argument(
        "status",
        type=str,
        help="New status (task: not_started/in_progress/completed/blocked, AC/SC: met/unmet)"
    )
    args = parser.parse_args()

    item_id = args.item_id.upper()
    status = args.status.lower()

    # Detect item type
    item_type = detect_item_type(item_id)
    if item_type is None:
        print(
            f"Error: Invalid item ID format: '{item_id}'. "
            f"Expected: TXXX (task), AC-XXX (acceptance criteria), or SC-XXX (success criteria)",
            file=sys.stderr
        )
        sys.exit(1)

    # Validate status for item type
    valid_statuses = get_valid_statuses(item_type)
    if status not in valid_statuses:
        print(
            f"Error: Invalid status '{status}' for {item_type}. "
            f"Valid statuses: {', '.join(valid_statuses)}",
            file=sys.stderr
        )
        sys.exit(1)

    # Get current version
    version = get_current_version()
    if not version:
        print("Error: Could not retrieve current_version from project/product/PRD.json", file=sys.stderr)
        sys.exit(1)

    # Get roadmap path
    roadmap_path = get_roadmap_path(version)
    if not roadmap_path.exists():
        print(f"Error: Roadmap not found at: {roadmap_path}", file=sys.stderr)
        sys.exit(1)

    # Load roadmap
    roadmap = load_roadmap(roadmap_path)
    if roadmap is None:
        print(f"Error: Could not load roadmap from: {roadmap_path}", file=sys.stderr)
        sys.exit(1)

    # Update based on item type
    if item_type == "task":
        success, message = update_task(roadmap, item_id, status)
    elif item_type == "ac":
        success, message = update_ac(roadmap, item_id, status)
    else:
        success, message = update_sc(roadmap, item_id, status)

    if not success:
        print(f"Error: {message}", file=sys.stderr)
        sys.exit(1)

    # Save roadmap
    if not save_roadmap(roadmap_path, roadmap):
        print(f"Error: Failed to save roadmap", file=sys.stderr)
        sys.exit(1)

    print(message)

    # Run auto-resolver
    resolver_success, resolutions = run_auto_resolver(version)
    for msg in resolutions:
        print(f"  {msg}")


if __name__ == "__main__":
    main()
