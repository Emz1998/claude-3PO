import json
from typing import Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook

from workflow.session_state import SessionState


REQUIRED_PHASES = [
    "task-creation",
    "exploration",
    "planning",
    "test",
    "code",
    "create-pr",
]


def main() -> None:
    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")

    hook_event_name = raw_input.get("hook_event_name", "")
    if hook_event_name != "PostToolUse":
        return

    tool_name = raw_input.get("tool_name", "")

    if tool_name != "ExitPlanMode":
        return

    session = SessionState(session_id)

    session.set_phases("completed", "planning")
    if session.TDD:
        session.set_phases("current", "test")
    else:
        session.set_phases("current", "code")


if __name__ == "__main__":
    main()
