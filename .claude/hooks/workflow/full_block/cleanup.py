"""PostToolUse handler — injects /simplify system message on new file creation during code phase."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.utils.normalize_tool import normalize_block_data


def cleanup_full_block(raw_input: dict[str, Any], session: SessionState) -> None:
    raw_tool_name = raw_input.get("tool_name", "")
    raw_tool_input = raw_input.get("tool_input", {})
    tool_name, tool_value = normalize_block_data(raw_tool_name, raw_tool_input)

    session.release("full_block", tool_name, tool_value)


def main() -> None:
    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")
    if not session_id:
        raise ValueError("Session ID is required")
    session = SessionState(session_id)
    if not session.workflow_active:
        return

    raw_input = Hook.read_stdin()
    cleanup_full_block(raw_input, session)


if __name__ == "__main__":
    cleanup_full_block(
        raw_input={
            "session_id": "123",
            "tool_name": "Skill",
            "tool_input": {"skill": "refactor"},
        },
        session=SessionState("123"),
    )
