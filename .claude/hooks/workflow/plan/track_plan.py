"""PostToolUse handler — injects /simplify system message on new file creation during code phase."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.state_store import StateStore
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.config import get as cfg
from workflow.utils.normalize_tool import normalize_block_data

STATE_FILE = Path(__file__).parent / "state.json"


def main() -> None:
    state = StateStore(STATE_FILE)
    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")
    if not session_id:
        raise ValueError("Session ID is required")
    session = SessionState(session_id)
    if not session.workflow_active:
        return

    file_path = raw_input.get("file_path", "")
    if not file_path:
        raise ValueError("File path is required")

    state.set("plan_file_path", file_path)


if __name__ == "__main__":
    state = StateStore(STATE_FILE)
    state.set("plan_file_path", "test.md")
