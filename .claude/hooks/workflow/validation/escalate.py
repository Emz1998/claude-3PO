"""Escalation handler — checks if validation was escalated to user."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.validation.validation_log import log
from workflow.session_state import SessionState
from workflow.config import get as cfg, get_reviewers

REVIEWER_AGENTS = get_reviewers()


def escalate(session: SessionState):
    story_id = session.story_id

    if story_id:
        session_data = session.get_session(story_id)
        if session_data:
            validation = session_data.get("validation", {})
        else:
            validation = {}
    else:
        # Fallback to flat state
        from workflow.state_store import StateStore
        store = StateStore(state_path=cfg("paths.workflow_state"))
        validation = store.get("validation") or {}

    escalate_flag = validation.get("escalate_to_user")
    escalated_by = validation.get("escalated_by")

    if escalate_flag:
        Hook.advanced_output(
            {"continue": False, "stopReason": f"Iteration Exhausted by {escalated_by}"}
        )


def main():
    hook_input = Hook.read_stdin()
    tool_input = hook_input.get("tool_input", {})
    agent_name = tool_input.get("subagent_type")

    if agent_name not in REVIEWER_AGENTS:
        return

    session = SessionState()
    escalate(session)


if __name__ == "__main__":
    main()
