#!/usr/bin/env python3
"""SubagentStop hook for workflow enforcement."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json

sys.path.insert(0, str(Path(__file__).parent))
from state import are_all_deliverables_met, get_state  # type: ignore
from roadmap.utils import are_all_scs_met_in_milestone  # type: ignore


def log(message: str) -> None:
    print(message, file=sys.stderr)


def block_subagent_stop(hook_input: dict, deliverables_met: bool) -> bool:
    hook_event = hook_input.get("hook_event_name", "")
    if hook_event != "SubagentStop":
        return False
    log(f"SubagentStop hook: deliverables_met={deliverables_met}")
    if not deliverables_met:
        decision = {
            "decision": "block",
            "reason": "Not all deliverables have been met",
        }
        print(json.dumps(decision))
        sys.exit(2)
    return True


def block_main_agent_stop(
    hook_input: dict, deliverables_met: bool, scs_met: bool
) -> bool:
    hook_event = hook_input.get("hook_event_name", "")
    if hook_event != "Stop":
        return False
    log(f"Stop hook: deliverables_met={deliverables_met}, scs_met={scs_met}")
    if not deliverables_met or not scs_met:
        reason = []
        if not deliverables_met:
            reason.append("deliverables not met")
        if not scs_met:
            reason.append("success criteria not met")
        decision = {
            "decision": "block",
            "reason": f"Cannot stop: {', '.join(reason)}",
        }
        print(json.dumps(decision))
        sys.exit(2)
    return True


def main() -> None:
    is_workflow_active = get_state("workflow_active")
    if not is_workflow_active:
        sys.exit(0)
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    deliverables_met = are_all_deliverables_met()
    scs_met = are_all_scs_met_in_milestone()

    handled = block_subagent_stop(hook_input, deliverables_met)
    if not handled:
        block_main_agent_stop(hook_input, deliverables_met, scs_met)

    sys.exit(0)


if __name__ == "__main__":
    main()
