#!/usr/bin/env python3
"""SubagentStop hook for workflow enforcement."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json

sys.path.insert(0, str(Path(__file__).parent))
from state import get_state, initialize_deliverables_state, set_state  # type: ignore


def main():
    is_workflow_active = get_state("workflow_active")
    if not is_workflow_active:
        sys.exit(0)
    hook_input = read_stdin_json()
    hook_event_name = hook_input.get("hook_event_name", "")

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    if hook_event_name != "PostToolUse":
        return

    if tool_name != "Skill":
        return
    skill_name = tool_input.get("skill", "")

    set_state("current_phase", skill_name)
    initialize_deliverables_state(phase=skill_name)


if __name__ == "__main__":
    main()
