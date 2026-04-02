"""task_guard.py — TaskCreated hook handler.

Validates task subject format during task-create phase.
Replaces task_recorder.py + task_list_recorder.py + task_validator.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore


def validate(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Validate a TaskCreated event.

    During task-create phase with a story_id set:
    - Blocks task creation if subject doesn't start with '{story_id}:'
    - Tracks created tasks count

    Returns ("allow", "") or ("block", reason).
    """
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    phase = state.get("phase", "")
    if phase != "task-create":
        # Outside task-create phase, allow any task
        return "allow", ""

    story_id = state.get("story_id")
    subject = hook_input.get("task_subject", "")

    if story_id:
        expected_prefix = f"{story_id}:"
        if not subject.startswith(expected_prefix):
            return (
                "block",
                f"Blocked: task subject must start with '{expected_prefix}' to match story ID. Got: '{subject}'. Prefix the subject with '{expected_prefix}'.",
            )

    return "allow", ""
