#!/usr/bin/env python3
"""TaskCompleted hook — marks child tasks done, auto-completes parent project tasks.

When a Claude task completes:
1. Find the parent project task via state.get_parent_for_subtask(task_id)
2. Mark the child subtask as completed
3. Check if all siblings are completed → mark parent as completed
4. If parent completed, update project_manager status to "Done"
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.hook import Hook
from lib.state_store import StateStore

STATE_PATH = SCRIPTS_DIR / "state.jsonl"
PROJECT_MANAGER = SCRIPTS_DIR / "github_project" / "project_manager.py"


def _update_project_task_status(task_id: str, status: str) -> None:
    """Call project_manager to update task status. Fire-and-forget."""
    try:
        subprocess.run(
            [sys.executable, str(PROJECT_MANAGER), "update", task_id, "--status", status],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass  # Non-critical — state is the source of truth


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(STATE_PATH, session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    # Only implement workflow tracks parent/child task relationships
    if state.get("workflow_type") != "implement":
        sys.exit(0)

    task_id = hook_input.get("task_id", "")
    if not task_id:
        sys.exit(0)

    # Find parent project task
    parent_id = state.get_parent_for_subtask(task_id)
    if not parent_id:
        sys.exit(0)

    # Mark child as completed
    state.set_subtask_completed(parent_id, task_id)

    # Check if all siblings are done → complete parent
    parent = next((pt for pt in state.project_tasks if pt.get("id") == parent_id), None)
    subs = parent.get("subtasks", []) if parent else []
    all_done = subs and all(
        (s.get("status") == "completed" if isinstance(s, dict) else False) for s in subs
    )
    if all_done:
        state.set_project_task_completed(parent_id)
        _update_project_task_status(parent_id, "Done")

    sys.exit(0)


if __name__ == "__main__":
    main()
