#!/usr/bin/env python3
"""Auto-resolver for roadmap with watchdog file watching."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PROJECT_DIR = Path(__file__).parent.parent.parent.parent
PRD_PATH = PROJECT_DIR / "project" / "product" / "PRD.json"


def get_roadmap_path() -> Path | None:
    """Get roadmap.json path from PRD current_version."""
    if not PRD_PATH.exists():
        return None
    try:
        prd = json.loads(PRD_PATH.read_text())
        version = prd.get("current_version", "")
        if not version:
            return None
        return PROJECT_DIR / "project" / version / "release-plan" / "roadmap.json"
    except (json.JSONDecodeError, IOError):
        return None


def load_roadmap(path: Path, retries: int = 3) -> dict | None:
    """Load roadmap from file with retry on failure."""
    for attempt in range(retries):
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, IOError):
            if attempt < retries - 1:
                time.sleep(0.1)
            continue
    return None


def save_roadmap(path: Path, data: dict) -> bool:
    """Save roadmap to file with updated timestamp."""
    try:
        if "metadata" in data:
            data["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[resolver] Save failed: {e}", file=sys.stderr)
        return False


def all_tasks_completed(milestone: dict) -> bool:
    """Check if all tasks in a milestone are completed."""
    tasks = milestone.get("tasks", [])
    if not tasks:
        return False
    return all(t.get("status") == "completed" for t in tasks)


def any_task_in_progress(milestone: dict) -> bool:
    """Check if any task in a milestone is in_progress."""
    tasks = milestone.get("tasks", [])
    return any(t.get("status") == "in_progress" for t in tasks)


def all_scs_met(milestone: dict) -> bool:
    """Check if all success criteria for a milestone are met."""
    scs = milestone.get("success_criteria", [])
    if not scs:
        return True
    return all(sc.get("status") == "met" for sc in scs)


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


def get_unmet_acs(task: dict) -> list[str]:
    """Get list of unmet acceptance criteria IDs for a task."""
    unmet = []
    for ac in task.get("acceptance_criteria", []):
        if ac.get("status") != "met":
            unmet.append(ac.get("id", "unknown"))
    return unmet


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

    all_completed = (
        all(p.get("status") == "completed" for p in phases) if phases else False
    )
    any_in_progress = any(p.get("status") == "in_progress" for p in phases)

    if current_status != "completed" and all_completed:
        roadmap["status"] = "completed"
        return "Project status -> 'completed'"
    elif current_status in ("not_started", "pending") and any_in_progress:
        roadmap["status"] = "in_progress"
        return "Project status -> 'in_progress'"
    elif current_status == "completed" and not all_completed:
        roadmap["status"] = "in_progress"
        return "Project status reverted -> 'in_progress'"
    return None


def get_task_by_id(roadmap: dict, task_id: str) -> dict | None:
    """Find a task by ID in the roadmap."""
    for phase in roadmap.get("phases", []):
        for milestone in phase.get("milestones", []):
            for task in milestone.get("tasks", []):
                if task.get("id") == task_id:
                    return task
    return None


def all_deps_completed(roadmap: dict, task: dict) -> bool:
    """Check if all task dependencies are completed."""
    deps = task.get("dependencies", [])
    if not deps:
        return True
    for dep_id in deps:
        dep_task = get_task_by_id(roadmap, dep_id)
        if dep_task and dep_task.get("status") != "completed":
            return False
    return True


def get_incomplete_deps(roadmap: dict, task: dict) -> list[str]:
    """Get list of incomplete dependency task IDs."""
    incomplete = []
    for dep_id in task.get("dependencies", []):
        dep_task = get_task_by_id(roadmap, dep_id)
        if dep_task and dep_task.get("status") != "completed":
            incomplete.append(dep_id)
    return incomplete


def resolve_tasks(roadmap: dict, milestone: dict) -> list[str]:
    """Auto-resolve tasks - enforce dependencies and AC requirements."""
    msgs = []
    for task in milestone.get("tasks", []):
        task_status = task.get("status")
        task_id = task.get("id")
        deps_met = all_deps_completed(roadmap, task)
        acs_met = all_acs_met(task)

        # Revert to not_started if dependencies not met
        if task_status in ("in_progress", "completed") and not deps_met:
            task["status"] = "not_started"
            incomplete = get_incomplete_deps(roadmap, task)
            msgs.append(
                f"Task '{task_id}' reverted -> 'not_started' (incomplete deps: {', '.join(incomplete)})"
            )
        # Revert completed task if ACs not met
        elif task_status == "completed" and not acs_met:
            task["status"] = "in_progress"
            unmet = get_unmet_acs(task)
            msgs.append(
                f"Task '{task_id}' reverted -> 'in_progress' (unmet ACs: {', '.join(unmet)})"
            )
    return msgs


def resolve_milestones_and_phases(roadmap: dict) -> list[str]:
    """Auto-resolve milestones and phases based on their children's status."""
    msgs = []
    phases = roadmap.get("phases", [])

    for phase in phases:
        milestones = phase.get("milestones", [])

        for milestone in milestones:
            # First resolve tasks
            task_msgs = resolve_tasks(roadmap, milestone)
            msgs.extend(task_msgs)
            current_status = milestone.get("status")
            tasks_completed = all_tasks_completed(milestone)
            scs_met = all_scs_met(milestone)
            has_task_in_progress = any_task_in_progress(milestone)

            # Revert completed milestone if tasks not done OR SCs not met
            if current_status == "completed" and (not tasks_completed or not scs_met):
                milestone["status"] = "in_progress"
                reasons = []
                if not tasks_completed:
                    reasons.append("incomplete tasks")
                if not scs_met:
                    unmet = get_unmet_scs(milestone)
                    reasons.append(f"unmet SCs: {', '.join(unmet)}")
                msgs.append(
                    f"Milestone '{milestone.get('id')}' reverted -> 'in_progress' ({', '.join(reasons)})"
                )
            # Revert in_progress milestone if no tasks in progress
            elif (
                current_status == "in_progress"
                and not has_task_in_progress
                and not tasks_completed
            ):
                milestone["status"] = "not_started"
                msgs.append(
                    f"Milestone '{milestone.get('id')}' reverted -> 'not_started' (no tasks in progress)"
                )
            # Auto-progress: pending -> in_progress when task starts
            elif current_status in ("pending", "not_started") and has_task_in_progress:
                milestone["status"] = "in_progress"
                msgs.append(f"Milestone '{milestone.get('id')}' -> 'in_progress'")
            # Auto-complete when all tasks done and SCs met
            elif current_status != "completed" and tasks_completed and scs_met:
                milestone["status"] = "completed"
                msgs.append(f"Milestone '{milestone.get('id')}' -> 'completed'")

        current_phase_status = phase.get("status")
        milestones_completed = all_milestones_completed(phase)
        has_milestone_in_progress = any_milestone_in_progress(phase)

        # Auto-progress: pending -> in_progress when milestone starts
        if (
            current_phase_status in ("pending", "not_started")
            and has_milestone_in_progress
        ):
            phase["status"] = "in_progress"
            msgs.append(f"Phase '{phase.get('id')}' -> 'in_progress'")
        # Auto-complete when all milestones done
        elif current_phase_status != "completed" and milestones_completed:
            phase["status"] = "completed"
            msgs.append(f"Phase '{phase.get('id')}' -> 'completed'")
        # Revert if completed but milestones not done
        elif current_phase_status == "completed" and not milestones_completed:
            phase["status"] = "in_progress"
            msgs.append(f"Phase '{phase.get('id')}' reverted -> 'in_progress'")

    return msgs


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
        for milestone in phase.get("milestones", []):
            if milestone.get("status") == "completed":
                continue
            new_milestone_id = milestone.get("id")
            for task in milestone.get("tasks", []):
                if task.get("status") == "completed":
                    continue
                new_task_id = task.get("id")
                break
            if new_task_id:
                break
        if new_milestone_id:
            break

    # Fallback to last items if all completed
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
        return f"Current -> phase={new_phase_id}, milestone={new_milestone_id}, task={new_task_id}"
    return None


def update_summary(roadmap: dict) -> None:
    """Update the summary section with current counts."""
    phases = roadmap.get("phases", [])

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

    roadmap["summary"] = {
        "phases": {
            "total": phase_total,
            "pending": phase_total - phase_completed,
            "completed": phase_completed,
        },
        "milestones": {
            "total": milestone_total,
            "pending": milestone_total - milestone_completed,
            "completed": milestone_completed,
        },
        "tasks": {
            "total": task_total,
            "pending": task_total - task_completed,
            "completed": task_completed,
        },
    }


def run_resolver() -> tuple[bool, list[str]]:
    """Run full auto-resolution."""
    path = get_roadmap_path()
    if not path or not path.exists():
        return False, ["Roadmap not found"]

    roadmap = load_roadmap(path)
    if not roadmap:
        return False, ["Failed to load roadmap"]

    msgs = resolve_milestones_and_phases(roadmap)

    if project_msg := resolve_project_status(roadmap):
        msgs.append(project_msg)

    if cur := update_current_pointer(roadmap):
        msgs.append(cur)

    update_summary(roadmap)

    if not save_roadmap(path, roadmap):
        return False, ["Failed to save"]

    return True, msgs


class RoadmapHandler(FileSystemEventHandler):
    """Watch roadmap.json and auto-resolve on changes."""

    def __init__(self):
        self._last = 0.0
        self._saving = False

    def on_modified(self, event):
        if event.is_directory or self._saving:
            return
        if not event.src_path.endswith("roadmap.json"):
            return
        if time.time() - self._last < 2.0:
            return
        self._last = time.time()

        self._saving = True
        try:
            time.sleep(0.2)  # Wait for write to complete
            ok, msgs = run_resolver()
            if msgs:
                for m in msgs:
                    print(f"[resolver] {m}", file=sys.stderr)
        finally:
            self._saving = False


def watch():
    """Start watching roadmap.json."""
    path = get_roadmap_path()
    if not path or not path.exists():
        print("[resolver] Roadmap not found", file=sys.stderr)
        return

    observer = Observer()
    observer.schedule(RoadmapHandler(), str(path.parent), recursive=False)
    observer.start()
    print(f"[resolver] Watching {path}", file=sys.stderr)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    watch()
