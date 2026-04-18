#!/usr/bin/env python3
"""TaskCompleted hook — propagate child completion up to the parent project task.

Serves the Claude Code ``TaskCompleted`` event for the ``implement`` workflow.
Flow:

    1. Read hook stdin; bail (``exit 0``) if no session_id, no active workflow,
       or the workflow isn't ``implement`` (only ``implement`` tracks
       parent/child task relationships).
    2. Look up the parent project task via
       ``state.get_parent_for_subtask(task_id)``. No parent → exit; this task
       isn't part of a tracked project breakdown.
    3. Mark the child subtask completed in state.
    4. If every sibling subtask is now completed, mark the parent completed and
       fire-and-forget a ``project_manager update`` CLI call to set its status
       to ``"Done"`` (state remains source of truth — the CLI sync is best-effort).

Always exits 0 — this hook is purely an observer; it never blocks.
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.hook import Hook
from lib.state_store import StateStore

STATE_PATH = SCRIPTS_DIR / "state.jsonl"
PLUGIN_ROOT = SCRIPTS_DIR.parent


def _update_project_task_status(task_id: str, status: str) -> None:
    """Fire-and-forget call to ``project_manager.cli`` to update task status.

    Best-effort by design: state.jsonl is the source of truth, so any failure
    here (CLI missing, timeout, OSError) is swallowed silently — the workflow
    continues with state already correct.

    Args:
        task_id (str): Project task id to update.
        status (str): New status string (e.g. ``"Done"``).

    Example:
        >>> _update_project_task_status("task-42", "Done")  # doctest: +SKIP
    """
    try:
        subprocess.run(
            [sys.executable, "-m", "project_manager.cli", "update", task_id, "--status", status],
            cwd=str(PLUGIN_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass  # Non-critical — state is the source of truth


def main() -> None:
    """Entry point — runs once per TaskCompleted event.

    Early-exit cascade: no session_id → no active workflow → workflow isn't
    ``implement`` → no task_id in payload → no parent project task →
    otherwise mark the child done and possibly cascade completion to the parent.

    Example:
        >>> main()  # doctest: +SKIP — reads JSON from stdin and exits
    """
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
