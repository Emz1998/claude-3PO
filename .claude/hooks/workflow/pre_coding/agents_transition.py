"""PostToolUse handler — injects /simplify system message on new file creation during code phase."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import StateStore
from workflow.session_state import SessionState
from workflow.utils.order_validation import validate_order
from workflow.config import get as cfg
from workflow.utils.resolve_session import resolve_session

AGENTS = cfg("agents")


def validate_transition(raw_input: dict, session: SessionState) -> None:
    current_agent = raw_input.get("tool_input", {}).get("current_agent", "")
    previous_agent = session.get("agent", {}).get("previous", "")

    is_valid, message = validate_order(current_agent, previous_agent, AGENTS)
    if not is_valid:
        Hook.block(message=message)
        return


def main() -> None:
    raw_input = Hook.read_stdin()
    session = resolve_session(raw_input)
    validate_transition(raw_input, session)


if __name__ == "__main__":
    main()
