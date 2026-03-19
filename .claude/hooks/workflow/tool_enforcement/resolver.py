"""PostToolUse handler — injects /simplify system message on new file creation during code phase."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.utils.normalize_tool import normalize_tool_data

TOOL_ORDER_LIST = [
    ("skill", "review"),
    ("command", "test"),
    ("skill", "refactor"),
    ("edit", "refactor"),
    ("agent", "refactor"),
    ("exit_plan_mode", None),
]


def get_next_tool(
    tool_data: tuple[str, str | None], tool_order_list: list[tuple[str, str | None]]
) -> tuple[str, str | None] | None:
    if tool_data not in tool_order_list:
        return None

    current_tool_idx = tool_order_list.index(tool_data)
    next_tool_idx = current_tool_idx + 1

    return tool_order_list[next_tool_idx]


def remove_tool(tool_data: tuple[str, str | None], session: SessionState) -> None:
    session.remove_enforced_tool(tool_data[0], tool_data[1])


def resolve_tool(
    tool_data: tuple[str, str | None],
    session: SessionState,
    tool_order_list: list[tuple[str, str | None]] = TOOL_ORDER_LIST,
) -> None:
    if session.tool_enforcement_status in ["bypass", "inactive"]:
        return

    next_tool_data = get_next_tool(tool_data, tool_order_list)

    if next_tool_data is None:
        print(f"Next tool not found")
        return

    next_tool_name, next_tool_value = next_tool_data

    session.enforce_tool(tool_name=next_tool_name, tool_value=next_tool_value)

    print(f"Next tool enforcement set")


def main() -> None:
    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")
    if not session_id:
        raise ValueError("Session ID is required")
    session = SessionState(session_id)
    if not session.workflow_active:
        return

    raw_tool_name = raw_input.get("tool_name", "")
    raw_tool_input = raw_input.get("tool_input", {})
    tool_data = normalize_tool_data(raw_tool_name, raw_tool_input)
    remove_tool(tool_data, session)
    resolve_tool(tool_data, session)


if __name__ == "__main__":
    remove_tool(
        tool_data=("Write", "src/main.py"),
        session=SessionState("123"),
    )
    resolve_tool(
        tool_data=("write", "src/utilss.py"),
        session=SessionState("123"),
    )
