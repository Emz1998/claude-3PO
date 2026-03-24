from typing import Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.guardrail.blocker import (
    block_exploration,
    block_planning,
    block_test_creation,
    block_coding,
)
from workflow.guardrail.validation import validate_test_file


def get_file_path(tool_name: str, tool_input: dict[str, Any]) -> str:
    if tool_name not in ["Write", "Edit"]:
        return ""

    return tool_input.get("file_path", "")


def get_agent(tool_name: str, tool_input: dict[str, Any]) -> str:
    if tool_name != "Agent":
        return ""

    return tool_input.get("subagent_type", "")


def setup_coding_guardrail(
    current_phase: str, tool_name: str, tool_input: dict[str, Any]
) -> None:

    file_path = get_file_path(tool_name, tool_input)

    if not file_path:
        return

    is_test, _ = validate_test_file(file_path)
    if is_test:
        return

    if current_phase != "coding":
        block_coding(file_path, "Coding is blocked for now")


def setup_test_guardrail(
    current_phase: str, tool_name: str, tool_input: dict[str, Any]
) -> None:

    file_path = get_file_path(tool_name, tool_input)

    if not file_path:
        return

    if current_phase != "test":
        block_test_creation(file_path, "Test is blocked for now")


def setup_planning_guardrail(
    current_phase: str, tool_name: str, tool_input: dict[str, Any]
) -> None:

    agent = get_agent(tool_name, tool_input)

    if not agent:
        return

    if current_phase != "planning":
        block_planning(agent, "Planning is blocked for now")


def setup_exploration_guardrail(
    current_phase: str, tool_name: str, tool_input: dict[str, Any]
) -> None:
    agent = get_agent(tool_name, tool_input)

    if not agent:
        return

    if current_phase != "exploration":
        block_exploration(agent, "Exploration is blocked for now")


def setup_guardrail(
    current_phase: str, tool_name: str, tool_input: dict[str, Any]
) -> None:
    setup_exploration_guardrail(current_phase, tool_name, tool_input)
    setup_planning_guardrail(current_phase, tool_name, tool_input)
    setup_test_guardrail(current_phase, tool_name, tool_input)
    setup_coding_guardrail(current_phase, tool_name, tool_input)


def main() -> None:
    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")
    tool_name = raw_input.get("tool_name", "")
    tool_input = raw_input.get("tool_input", {})
    session = SessionState(session_id)
    current_phase = session.current_phase
    setup_guardrail(current_phase, tool_name, tool_input)


if __name__ == "__main__":
    main()
