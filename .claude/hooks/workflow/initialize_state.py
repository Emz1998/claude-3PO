"""Initialize workflow state on UserPromptSubmit."""

from pathlib import Path

from workflow.state_store import StateStore
from workflow.hook import Hook
from workflow.config import get as cfg
from workflow.models.hook_input import UserPromptSubmitInput

PATH = Path(cfg("paths.workflow_state"))


def initialize_state(hook_input: UserPromptSubmitInput) -> None:
    state_store = StateStore(PATH)
    state = state_store.load()
    # Preserve sessions if they exist, only reset ephemeral keys
    sessions = state.get("sessions", {})
    state_store.save(
        {
            "sessions": sessions,
            "workflow_active": state.get("workflow_active", False),
        }
    )
