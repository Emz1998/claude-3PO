"""PostToolUse handler — injects /simplify system message on new file creation during code phase."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.state_store import StateStore
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate

STATE_FILE = Path(__file__).parent / "state.json"


def main() -> None:
    state = StateStore(STATE_FILE)
    session = SessionState("123")
    if not check_workflow_gate():
        return

    plan_file_path = state.get("plan_file_path", "")
    if not plan_file_path:
        Hook.block(
            message="Less than 3 explore agents are running. Please run at least 3 explore agents."
        )
        return

    session.add(
        list_type="full_block",
        tool_name="ExitPlanMode",
        tool_value=None,
        reason="Please exit plan mode first",
    )


if __name__ == "__main__":
    main()
