#!/usr/bin/env python3
"""SubagentStop hook for workflow enforcement."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json

sys.path.insert(0, str(Path(__file__).parent))
from state import are_all_deliverables_met, get_state, set_state  # type: ignore
from roadmap.utils import are_all_scs_met_in_milestone  # type: ignore


def log(message: str) -> None:
    print(message, file=sys.stderr)


def block_subagent_stop(hook_input: dict, deliverables_met: bool) -> bool:
    hook_event = hook_input.get("hook_event_name", "")
    if hook_event != "SubagentStop":
        return False
    if not deliverables_met:
        decision = {
            "decision": "block",
            "reason": "Not all deliverables have been met",
        }
        print(json.dumps(decision))
        sys.exit(2)
    return True


def main() -> None:
    is_workflow_active = get_state("workflow_active")
    if not is_workflow_active:
        sys.exit(0)
    hook_input = read_stdin_json()
    hook_event_name = hook_input.get("hook_event_name", "")
    if not hook_input:
        sys.exit(0)

    deliverables_met, deliverables_message = are_all_deliverables_met()

    if hook_event_name != "SubagentStop":
        sys.exit(0)
    if not deliverables_met:
        set_state("subagent_status", "blocked")
        decision = {
            "decision": "block",
            "reason": deliverables_message,
        }
        print(json.dumps(decision))
        sys.exit(2)

    set_state("subagent_status", "allowed")
    sys.exit(0)


if __name__ == "__main__":
    main()
