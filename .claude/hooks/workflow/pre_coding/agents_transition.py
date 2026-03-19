"""PostToolUse handler — injects /simplify system message on new file creation during code phase."""

import sys
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import StateStore
from workflow.session_state import SessionState
from workflow.utils.order_validation import validate_order
from workflow.config import get as cfg
from workflow.utils.resolve_session import resolve_session
from workflow.tool_enforcement.resolver import resolve_tool
from workflow.utils.normalize_tool import normalize_tool_data

PHASE = [
    ("agent", "Explore"),
    ("agent", "Plan"),
    ("agent", "plan-reviewer"),
]


def main() -> None:
    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")
    if not session_id:
        raise ValueError("Session ID is required")
    session = SessionState(session_id)
    if not session.workflow_active:
        return
    raw_tool_name = raw_input.get("tool_name", "")
    raw_tool_value = raw_input.get("tool_input", {}).get("current_agent", "")
    tool_data = normalize_tool_data(raw_tool_name, raw_tool_value)
    agents = cast(list[tuple[str, str | None]], PHASE)
    resolve_tool(tool_data, session, agents)


if __name__ == "__main__":
    main()
