#!/usr/bin/env python3
"""PreToolUse hook for subagent invocation validation.

Validates that the correct subagent is being invoked for the current workflow phase.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from state import get_state  # type: ignore
from phases import PHASE_SUBAGENTS  # type: ignore


def is_subagent_allowed_in_phase(
    phase_name: str, subagent_name: str, allowed_list: dict[str, str] | None = None
) -> bool:
    """Check if a subagent is allowed to run in the given phase."""
    if not allowed_list:
        allowed_list = PHASE_SUBAGENTS
    return allowed_list.get(phase_name) == subagent_name


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
    if tool_name != "Task":
        sys.exit(0)

    current_phase = get_state("current_phase")
    subagent = hook_input.get("tool_input", {}).get("subagent_type", "")
    subagent_allowed = is_subagent_allowed_in_phase(current_phase, subagent)

    if not subagent_allowed:
        print(f'Subagent "{subagent}" not allowed in phase "{current_phase}"', file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
