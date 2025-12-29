#!/usr/bin/env python3
"""Reset roadmap to default state with all tasks pending."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.roadmap import (  # type: ignore
    get_current_version,
    get_roadmap_path,
    load_roadmap,
    save_roadmap,
)


DEFAULT_STATUS = {
    "phase": "not_started",
    "milestone": "not_started",
    "task": "not_started",
    "acceptance_criteria": "unmet",
    "success_criteria": "unmet",
}


def reset_roadmap() -> None:
    """Reset all roadmap items to not_started/unmet status."""
    try:
        version = get_current_version()
        if not version:
            print(
                "Error: Could not retrieve current_version from PRD.json",
                file=sys.stderr,
            )
            sys.exit(1)

        roadmap_path = get_roadmap_path(version)
        roadmap = load_roadmap(roadmap_path)
        if roadmap is None:
            print(
                f"Error: Could not load roadmap from: {roadmap_path}", file=sys.stderr
            )
            sys.exit(1)

        # Reset project-level status
        roadmap["status"] = "not_started"

        phases = roadmap.get("phases", [])
        task_count = 0
        milestone_count = 0
        phase_count = len(phases)

        for phase in phases:
            phase["status"] = DEFAULT_STATUS["phase"]

            milestones = phase.get("milestones", [])
            milestone_count += len(milestones)

            for milestone in milestones:
                milestone["status"] = DEFAULT_STATUS["milestone"]

                # Reset success criteria
                for sc in milestone.get("success_criteria", []):
                    sc["status"] = DEFAULT_STATUS["success_criteria"]

                tasks = milestone.get("tasks", [])
                task_count += len(tasks)

                for task in tasks:
                    task["status"] = DEFAULT_STATUS["task"]

                    # Reset acceptance criteria
                    for ac in task.get("acceptance_criteria", []):
                        ac["status"] = DEFAULT_STATUS["acceptance_criteria"]

        # Reset current pointer to first task
        if phases:
            first_phase = phases[0]
            first_milestone = (
                first_phase.get("milestones", [{}])[0]
                if first_phase.get("milestones")
                else {}
            )
            first_task = (
                first_milestone.get("tasks", [{}])[0]
                if first_milestone.get("tasks")
                else {}
            )

            roadmap["current"] = {
                "phase": first_phase.get("id", ""),
                "milestone": first_milestone.get("id", ""),
                "task": first_task.get("id", ""),
            }

        # Reset summary counts
        roadmap["summary"] = {
            "phases": {
                "total": phase_count,
                "pending": phase_count,
                "completed": 0,
            },
            "milestones": {
                "total": milestone_count,
                "pending": milestone_count,
                "completed": 0,
            },
            "tasks": {
                "total": task_count,
                "pending": task_count,
                "completed": 0,
            },
        }

        if not save_roadmap(roadmap_path, roadmap):
            print("Error: Failed to save roadmap", file=sys.stderr)
            sys.exit(1)

        print(f"Roadmap reset successfully:")
        print(f"  - {phase_count} phases reset to not_started")
        print(f"  - {milestone_count} milestones reset to not_started")
        print(f"  - {task_count} tasks reset to not_started")
        print(f"  - All acceptance/success criteria reset to unmet")

    except Exception as e:
        print(f"Roadmap reset error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    reset_roadmap()
