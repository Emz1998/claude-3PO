#!/usr/bin/env python3
"""Auto-resolver for roadmap milestones and phases."""

from .roadmap import (
    get_current_version,
    get_roadmap_path,
    load_roadmap,
    save_roadmap,
    all_tasks_completed,
    all_scs_met,
    any_task_in_progress,
    all_milestones_completed,
    any_milestone_in_progress,
    get_unmet_scs,
)


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
        if (
            current_phase_status in ("pending", "not_started")
            and has_milestone_in_progress
        ):
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


def run_auto_resolver() -> tuple[bool, list[str]]:
    """Run the auto-resolver for milestones and phases."""
    version = get_current_version()
    if not version:
        return False, [
            "Could not retrieve current_version from project/product/PRD.json"
        ]

    roadmap_path = get_roadmap_path(version)
    roadmap = load_roadmap(roadmap_path)
    if roadmap is None:
        return False, [f"Could not load roadmap from: {roadmap_path}"]

    resolutions = resolve_milestones_and_phases(roadmap)

    current_msg = update_current_pointer(roadmap)
    if current_msg:
        resolutions.append(current_msg)

    update_summary(roadmap)
    if not save_roadmap(roadmap_path, roadmap):
        return False, ["Failed to save roadmap after auto-resolution"]

    return True, resolutions
