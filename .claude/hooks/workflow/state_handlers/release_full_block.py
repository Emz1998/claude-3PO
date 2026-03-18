import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.config import get as cfg


def full_release(session: SessionState) -> None:
    session.set(
        "fully_blocked",
        {
            "status": "inactive",
            "reason": None,
            "list": None,
        },
    )


def release_full_block(input_tool_name: str, input_tool_value: Any) -> None:
    session = SessionState(Path(cfg("paths.workflow_state")))
    fully_blocked = session._fully_blocked
    exceptions = fully_blocked.get("exception", [["skill", "refactor"]])
    if not input_tool_name or not input_tool_value:
        raise ValueError("input_tool_name and input_tool_value must be provided")

    if not isinstance(exceptions, list):
        return

    for exception in exceptions:
        if exception == [input_tool_name, input_tool_value]:
            exceptions.remove(exception)

    if not exceptions:
        full_release(session)
        return

    session.set(
        "fully_blocked",
        {
            **fully_blocked,
            "exception": exceptions,
        },
    )
