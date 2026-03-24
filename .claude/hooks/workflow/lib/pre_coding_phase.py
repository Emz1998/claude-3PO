"""PreToolUse handler — validates workflow phase ordering."""

from typing import Any, Generic, TypeVar, cast
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.models.hook_input import PreToolUseInput, PostToolUseInput, StopInput
from workflow.workflow_gate import check_workflow_gate
from workflow.utils.order_validation import validate_order
from workflow.config import get as cfg


def validate_transition(
    raw_input: dict[str, Any], session: SessionState
) -> tuple[bool, str]:
    previous_agent = session.previous_agent
    current_agent = raw_input.get("tool_input", {}).get("subagent_type", None)
    if current_agent is None:
        raise ValueError("subagent-type key is not found in hook input")
    return validate_order(previous_agent, current_agent, cfg("agents.pre_coding"))


def main() -> None:
    session = SessionState()

    if not session.workflow_active:
        return

    if not session.plan_mode:
        Hook.block("Please enter plan mode (EnterPlanMode) first.")
        return

    raw_input = Hook.read_stdin()

    is_valid, reason = validate_transition(raw_input, session)
    if not is_valid:
        Hook.block(reason)


if __name__ == "__main__":
    main()
