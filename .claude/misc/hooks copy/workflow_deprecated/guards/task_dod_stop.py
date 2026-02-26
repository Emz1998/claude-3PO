#!/usr/bin/env python3
"""Stop guard for task DoD enforcement.

Blocks agent stop if current tasks' DoD is not met (not all tasks completed).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore


class TaskDodStopGuard:
    """Guard that blocks Stop if tasks are incomplete."""

    def __init__(self):
        """Initialize the guard."""
        self._state = get_manager()

    def is_active(self) -> bool:
        """Check if guard is active (workflow is active)."""
        return self._state.is_workflow_active()

    def get_incomplete_tasks(self) -> list[str]:
        """Get list of incomplete task IDs from project state."""
        from release_plan.state import load_project_state  # type: ignore

        project_state = load_project_state() or {}

        current_tasks = project_state.get("current_tasks", {})
        return [
            task_id
            for task_id, status in current_tasks.items()
            if status != "completed"
        ]

    def run(self, hook_input: dict) -> None:
        """Run the guard against hook input.

        Args:
            hook_input: The hook input dictionary
        """
        if not self.is_active():
            sys.exit(0)

        incomplete = self.get_incomplete_tasks()
        if incomplete:
            task_list = ", ".join(incomplete)
            decision = {
                "decision": "block",
                "reason": f"Task DoD not met. Incomplete: {task_list}",
            }
            print(json.dumps(decision))
            sys.exit(2)

        sys.exit(0)


def main() -> None:
    """Main entry point for the guard."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    guard = TaskDodStopGuard()
    guard.run(hook_input)


if __name__ == "__main__":
    main()
