import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.config import get as cfg


def full_release(session: SessionState) -> None:
    session.set(
        "tool_block",
        {
            "status": "inactive",
            "reason": None,
            "list": None,
        },
    )


def release_tool_block(input_tool_name: str, input_tool_value: Any) -> None:
    session = SessionState(Path(cfg("paths.workflow_state")))
    tool_block = session._tool_block
    tools_to_block_list = tool_block.get("list", [["skill", "refactor"]])
    if not input_tool_name or not input_tool_value:
        raise ValueError("input_tool_name and input_tool_value must be provided")

    if not isinstance(tools_to_block_list, list):
        return

    for tool_name, tool_value in tools_to_block_list:
        if tool_name != input_tool_name:
            continue
        if tool_value != input_tool_value:
            continue
        tools_to_block_list.remove([tool_name, tool_value])

    if not tools_to_block_list:
        full_release(session)
        return

    session.set(
        "tool_block",
        {
            **tool_block,
            "list": tools_to_block_list,
        },
    )
