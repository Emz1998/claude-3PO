"""utils.hooks.task_completed — orchestration helpers for the TaskCompleted hook.

Extracted from ``dispatchers/task_completed.py`` so the dispatcher file holds
only ``main()``. The helper here is the fire-and-forget project_manager sync.
"""

import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
PLUGIN_ROOT = SCRIPTS_DIR.parent


def update_project_task_status(task_id: str, status: str) -> None:
    """Fire-and-forget call to ``project_manager.cli`` to update task status.

    Best-effort by design: state.jsonl is the source of truth, so any failure
    here (CLI missing, timeout, OSError) is swallowed silently — the workflow
    continues with state already correct.

    Args:
        task_id (str): Project task id to update.
        status (str): New status string (e.g. ``"Done"``).

    Example:
        >>> update_project_task_status("task-42", "Done")  # doctest: +SKIP

    SideEffect:
        Runs ``python -m project_manager.cli update ...`` in a subprocess
        and ignores its exit status.
    """
    # 15s timeout plus broad except catches the three realistic failure modes:
    # CLI not installed, hang, or OS-level spawn error. State is already
    # correct locally, so silent failure is acceptable here.
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
