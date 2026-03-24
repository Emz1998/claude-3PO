"""PreToolUse handler — validates coding phase agent ordering."""

from typing import Any, cast
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.models.hook_input import PreToolUseInput
from workflow.utils.order_validation import validate_order
from workflow.config import get as cfg
from workflow.state_store import StateStore


def resolve_coding_agents(session: SessionState) -> list[str]:
    if session.TDD:
        return cfg("agents.test").append("code-reviewer")
    return ["code-reviewer"]


def resolve_agents_list(session: SessionState) -> list[str]:
    match session.current_phase:
        case "pre_coding":
            return cfg("agents.pre_coding")
        case "code":
            return resolve_coding_agents(session)
        case _:
            raise ValueError(f"Invalid phase: {session.current_phase}")


def validate_transition(
    raw_input: dict[str, Any], session: SessionState
) -> tuple[bool, str]:
    previous_phase = session.previous_phase
    current_phase = raw_input.get("tool_input", {}).get("skill", None)
    if current_phase is None:
        raise ValueError("skill key is not found in hook input")
    return validate_order(previous_phase, current_phase, resolve_agents_list(session))


def main() -> None:
    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")
    if not session_id:
        raise ValueError("Session ID is required")
    session = SessionState(session_id)

    if not session.workflow_active:
        return

    if not session.plan_mode:
        Hook.block("Please enter plan mode (EnterPlanMode) first.")
        return

    is_valid, reason = validate_transition(raw_input, session)
    if not is_valid:
        Hook.block(reason)


if __name__ == "__main__":
    main()
