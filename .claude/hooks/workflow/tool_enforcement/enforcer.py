"""PostToolUse handler — injects /simplify system message on new file creation during code phase."""

import sys
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.utils.normalize_tool import normalize_tool_data

TEMPLATE_REASON = """
{tool_name} '{tool_value}' is blocked by tool enforcement.

Only the following tools are allowed:

{enforced_tools}
"""


def format_enforced_tools(enforced_tools: list[tuple[str, str | None]]) -> str:
    return "\n".join(
        [
            f"- {tool_name.capitalize()}: {tool_value}"
            for tool_name, tool_value in enforced_tools
        ]
    )


def format_reason(
    tool_name: str, tool_value: str | None, enforced_tools: list[tuple[str, str | None]]
) -> str:

    return TEMPLATE_REASON.format(
        tool_name=tool_name.capitalize(),
        tool_value=tool_value,
        enforced_tools=format_enforced_tools(enforced_tools),
    )


def validate_enforced_tool(
    raw_tool_name: str, raw_tool_input: dict[str, Any], session: SessionState
) -> None:

    received_tool = normalize_tool_data(raw_tool_name, raw_tool_input)

    for enforced_tool in session.enforced_tools:
        if received_tool == tuple(enforced_tool):
            return

    enforced_tools = cast(list[tuple[str, str | None]], session.enforced_tools)

    Hook.block(
        message=format_reason(received_tool[0], received_tool[1], enforced_tools)
    )


def main() -> None:
    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")
    if not session_id:
        raise ValueError("Session ID is required")
    session = SessionState(session_id)
    if not session.workflow_active:
        return

    raw_input = Hook.read_stdin()
    validate_enforced_tool(
        raw_tool_name=raw_input.get("tool_name", ""),
        raw_tool_input=raw_input.get("tool_input", {}),
        session=session,
    )


if __name__ == "__main__":
    main()
