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


def main() -> None:
    is_workflow_active = get_state("workflow_active")
    if not is_workflow_active:
        sys.exit(0)
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    deliverables_met, message = are_all_deliverables_met()
    scs_met, scs_message = are_all_scs_met_in_milestone()

    if not deliverables_met or not scs_met:
        decision = {
            "decision": "block",
            "reason": message if deliverables_met else scs_message,
        }
        print(json.dumps(decision))
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
