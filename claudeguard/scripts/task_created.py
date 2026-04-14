#!/usr/bin/env python3
"""TaskCreated hook — validates and records task creation.

Build workflow: matches task_subject against state.tasks (from plan ## Tasks).
Implement workflow: matches task_subject against project_tasks titles,
records child task under the parent with task_id and status.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.hook import Hook
from utils.state_store import StateStore
from utils.violations import log_violation

STATE_PATH = Path(os.environ.get(
    "TASK_CREATED_STATE_PATH",
    str(Path(__file__).resolve().parent / "state.jsonl"),
))


def _block(reason: str, state: StateStore, session_id: str, task_subject: str) -> None:
    """Log violation and block."""
    log_violation(
        session_id=session_id,
        workflow_type=state.get("workflow_type", "build"),
        story_id=state.get("story_id"),
        prompt_summary=state.get("prompt_summary"),
        phase=state.current_phase,
        tool="TaskCreate",
        action=task_subject,
        reason=reason,
    )
    Hook.block(reason)


def _match_substring(subject: str, candidates: list[str]) -> str | None:
    """Case-insensitive substring match. Returns the matched candidate or None."""
    normalized = subject.strip().lower()
    for c in candidates:
        c_lower = c.strip().lower()
        if normalized == c_lower or c_lower in normalized or normalized in c_lower:
            return c
    return None


def _validate_build(task_subject: str, state: StateStore, session_id: str) -> None:
    """Build workflow: match against plan's ## Tasks bullets, record creation."""
    planned_tasks = state.tasks

    if not planned_tasks:
        _block("No planned tasks found in state. Create a plan with ## Tasks first.",
               state, session_id, task_subject)

    matched = _match_substring(task_subject, planned_tasks)
    if not matched:
        _block(
            f"Task '{task_subject}' does not match any planned task.\n"
            f"Planned tasks: {planned_tasks}",
            state, session_id, task_subject,
        )

    # Record that this planned task has been created
    state.add_created_task(matched)


def _validate_implement(
    task_id: str, task_subject: str, state: StateStore, session_id: str
) -> None:
    """Implement workflow: match against project_tasks titles, record child."""
    project_tasks = state.project_tasks

    if not project_tasks:
        _block(
            "No project tasks found in state. "
            "The create-tasks phase must load tasks from the project manager first.",
            state, session_id, task_subject,
        )

    # Find parent by matching subject to project task title
    titles = [pt.get("title", "") for pt in project_tasks]
    matched_title = _match_substring(task_subject, titles)

    if not matched_title:
        _block(
            f"Task '{task_subject}' does not match any project task.\n"
            f"Project tasks: {titles}",
            state, session_id, task_subject,
        )

    # Record child task under the matched parent
    for pt in project_tasks:
        if pt.get("title", "").strip().lower() == matched_title.strip().lower():
            state.add_subtask(pt["id"], {
                "task_id": task_id,
                "subject": task_subject,
                "status": "in_progress",
            })
            break


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(STATE_PATH, session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    task_id = hook_input.get("task_id", "")
    task_subject = hook_input.get("task_subject", "")
    task_description = hook_input.get("task_description", "")

    # Common validation
    if not task_description or not task_description.strip():
        _block("Task must have a non-empty description.", state, session_id, task_subject)

    if not task_subject or not task_subject.strip():
        _block("Task must have a non-empty subject.", state, session_id, task_subject)

    # Dispatch by workflow type
    workflow_type = state.get("workflow_type", "build")
    if workflow_type == "implement":
        _validate_implement(task_id, task_subject, state, session_id)
    else:
        _validate_build(task_subject, state, session_id)

    sys.exit(0)


if __name__ == "__main__":
    main()
