#!/usr/bin/env python3
"""Phase transition guard hook for workflow enforcement."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json  # type: ignore
from roadmap.utils import get_current, get_test_strategy  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from state import get_state  # type: ignore

PHASE_SUBAGENTS = {
    "explore": "codebase-explorer",
    "plan": "planner",
    "plan-consult": "plan-consultant",
    "commit": "version-manager",
    "write_test": "test-engineer",
    "review_test": "test-reviewer",
    "write-code": "main-agent",
    "review_code": "code-reviewer",
    "refactor": "main-agent",
    "validate": "validator",
    "commit": "version-manager",
}


def is_subagent_allowed_in_phase(
    phase_name: str, subagent_name: str, allowed_list: dict[str, str] | None = None
) -> bool:
    if not allowed_list:
        allowed_list = PHASE_SUBAGENTS
    return allowed_list[phase_name] == subagent_name


def main() -> None:
    is_workflow_active = get_state("workflow_active")
    if not is_workflow_active:
        sys.exit(0)
    hook_input = read_stdin_json()

    hook_event_name = hook_input.get("hook_event_name", "")
    if hook_event_name != "PreToolUse":
        return

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Task":
        sys.exit(0)

    print("Checking if subagent allowed")

    current_phase = get_state("current_phase")
    subagent = hook_input.get("tool_input", {}).get("subagent_type", "")
    subagent_allowed = is_subagent_allowed_in_phase(current_phase, subagent)
    if not subagent_allowed:
        print(f'Subagent "{subagent}" not allowed in this phase ', file=sys.stderr)
        sys.exit(2)
    print("Subagent allowed")
    sys.exit(0)


if __name__ == "__main__":
    main()
