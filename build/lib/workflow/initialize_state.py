from pathlib import Path

from workflow.state_store import StateStore
from workflow.hook import Hook, UserPromptSubmit

PATH = Path(__file__).resolve().parent / "state.json"


def initialize_state(hook: Hook[UserPromptSubmit]) -> None:
    state_store = StateStore(PATH)
    state_store.save(
        {
            "recent_phase": "",
            "recent_coding_phase": "",
        }
    )
