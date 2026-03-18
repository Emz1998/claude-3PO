"""Workflow gate — controls whether workflow handlers execute.

Handlers that activate the workflow (build_entry, implement_trigger) set
workflow_active=True in sprint state. All other handlers call
check_workflow_gate() to skip when the workflow is inactive.
"""

from typing import Any
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workflow.state_store import StateStore
from workflow.config import get as cfg

PATH = Path(cfg("paths.workflow_state"))
WORKFLOW_ACTIVE_KEY = "workflow_active"

state_store = StateStore(PATH, default_state={WORKFLOW_ACTIVE_KEY: False})


def is_workflow_active(state: dict[str, Any]) -> bool:
    """Check if the workflow is active from a state dict."""
    return state.get(WORKFLOW_ACTIVE_KEY, False) is True


def activate_workflow() -> None:
    """Set workflow_active=True in sprint state and persist."""
    state_store.set(WORKFLOW_ACTIVE_KEY, True)


def deactivate_workflow() -> None:
    """Set workflow_active=False in sprint state and persist."""
    state_store.set(WORKFLOW_ACTIVE_KEY, False)


def check_workflow_gate() -> bool:
    """Load sprint state and return True if workflow is active.

    Handlers should call this at the top and return early if False.
    """
    state = StateStore(PATH).load()
    if state is None:
        return False
    return is_workflow_active(state)
