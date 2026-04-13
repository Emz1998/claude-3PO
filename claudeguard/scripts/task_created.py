#!/usr/bin/env python3
"""TaskCreated hook — validates task matches planned tasks."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.hook import Hook
from utils.state_store import StateStore

STATE_PATH = Path(os.environ.get(
    "TASK_CREATED_STATE_PATH",
    str(Path(__file__).resolve().parent / "state.json"),
))


def main() -> None:
    hook_input = Hook.read_stdin()

    state = StateStore(STATE_PATH)
    if not state.get("workflow_active"):
        sys.exit(0)
    if hook_input.get("session_id") != state.get("session_id"):
        sys.exit(0)

    task_subject = hook_input.get("task_subject", "")
    task_description = hook_input.get("task_description", "")
    planned_tasks = state.tasks

    # Validate task description is present and non-empty
    if not task_description or not task_description.strip():
        Hook.block("Task must have a non-empty description.")

    # Validate subject is non-empty
    if not task_subject or not task_subject.strip():
        Hook.block("Task must have a non-empty subject.")

    # Block if no planned tasks exist
    if not planned_tasks:
        Hook.block(f"No planned tasks found in state. Create a plan with ## Tasks first.")

    # Normalize and match
    normalized_subject = task_subject.strip().lower()
    matched = any(
        normalized_subject == t.strip().lower()
        or t.strip().lower() in normalized_subject
        or normalized_subject in t.strip().lower()
        for t in planned_tasks
    )

    if not matched:
        Hook.block(
            f"Task '{task_subject}' does not match any planned task.\n"
            f"Planned tasks: {planned_tasks}"
        )

    # Allow
    sys.exit(0)


if __name__ == "__main__":
    main()
