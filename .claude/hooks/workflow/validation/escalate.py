import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.validation.validation_log import log
from workflow.state_store import StateStore
from workflow.config import get as cfg, get_reviewers

REVIEWER_AGENTS = get_reviewers()


def escalate():
    state = StateStore(state_path=cfg("paths.workflow_state"))
    validation = state.get("validation")
    escalate = validation.get("escalate_to_user")
    escalated_by = validation.get("escalated_by")

    if escalate:
        Hook.advanced_output(
            {"continue": False, "stopReason": f"Iteration Exhausted by {escalated_by}"}
        )


def main():

    hook_input = Hook.read_stdin()
    tool_input = hook_input.get("tool_input", {})
    agent_name = tool_input.get("subagent_type")

    if agent_name not in REVIEWER_AGENTS:
        return

    escalate()


if __name__ == "__main__":
    main()
