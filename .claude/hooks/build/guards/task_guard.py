"""task_guard.py — Lightweight TaskCreate handler for /build.

No story ID validation, no project manager lookup.
Just tracks that tasks were created and auto-advances phase.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from build.session_store import SessionStore


def validate(hook_input: dict, store: SessionStore) -> tuple[str, str]:
    """Allow TaskCreate during task-create phase, track it in state."""
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    phase = state.get("phase", "")
    if phase != "task-create":
        return "allow", ""

    tool_input = hook_input.get("tool_input", {})
    subject = tool_input.get("subject", "")
    description = tool_input.get("description", "")

    def _record_and_advance(s: dict) -> None:
        tasks = s.setdefault("tasks", [])
        tasks.append({
            "subject": subject,
            "description": description,
            "status": "pending",
        })
        # Auto-advance after first task is created
        if s.get("phase") == "task-create":
            if s.get("tdd"):
                s["phase"] = "write-tests"
            else:
                s["phase"] = "write-code"

    store.update(_record_and_advance)
    return "allow", ""


def validate_completed(hook_input: dict, store: SessionStore) -> tuple[str, str]:
    """Handle TaskCompleted — update task status. Always allows."""
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    task_subject = hook_input.get("task_subject", "")
    if not task_subject:
        return "allow", ""

    def _update_status(s: dict) -> None:
        for task in s.get("tasks", []):
            if task["subject"] == task_subject and task["status"] == "pending":
                task["status"] = "completed"
                return

    store.update(_update_status)
    return "allow", ""
