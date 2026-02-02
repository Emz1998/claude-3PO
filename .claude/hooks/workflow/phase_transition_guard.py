#!/usr/bin/env python3
"""PreToolUse hook for phase transition validation.

Validates that phase transitions follow the defined order based on test strategy.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from state import get_state  # type: ignore
from _utils import validate_order  # type: ignore
from phases import get_phase_order  # type: ignore


def main() -> None:
    is_workflow_active = get_state("workflow_active")
    if not is_workflow_active:
        sys.exit(0)

    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    hook_event_name = hook_input.get("hook_event_name", "")
    if hook_event_name != "PreToolUse":
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Skill":
        sys.exit(0)

    current_phase = get_state("current_phase")
    phase_order = get_phase_order("tdd")
    skill = hook_input.get("tool_input", {}).get("skill", "")

    is_valid, error_message = validate_order(current_phase, skill, phase_order)
    if not is_valid:
        print(error_message, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
