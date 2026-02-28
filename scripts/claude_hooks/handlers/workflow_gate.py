"""Workflow gate — controls whether workflow handlers execute.

Handlers that activate the workflow (build_entry, implement_trigger) set
workflow_active=True in sprint state. All other handlers call
check_workflow_gate() to skip when the workflow is inactive.
"""

from typing import Any

from pathlib import Path
from scripts.claude_hooks.file_manager import FileManager

WORKFLOW_ACTIVE_KEY = "workflow_active"

FLAG_FILE = Path.cwd() / "project/tmp/tmp_state.json"


def is_workflow_active(state: dict[str, Any]) -> bool:
    """Check if the workflow is active from a state dict."""
    return state.get(WORKFLOW_ACTIVE_KEY, False) is True


def activate_workflow() -> None:
    """Set workflow_active=True in sprint state and persist."""
    state = FileManager(FLAG_FILE).load()
    if state is None:
        state = {}
    state[WORKFLOW_ACTIVE_KEY] = True
    FileManager(FLAG_FILE).save(state)


def check_workflow_gate() -> bool:
    """Load sprint state and return True if workflow is active.

    Handlers should call this at the top and return early if False.
    """
    state = FileManager(FLAG_FILE).load()
    if state is None:
        return False
    return is_workflow_active(state)


if __name__ == "__main__":
    activate_workflow()
    print(check_workflow_gate())
