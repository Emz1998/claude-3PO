#!/usr/bin/env python3
"""SubagentStop hook for workflow enforcement."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json
from roadmap.utils import (
    are_all_tasks_completed_in_milestone,
    are_all_scs_met_in_milestone,
)

sys.path.insert(0, str(Path(__file__).parent))
from state import are_all_deliverables_met, get_state, log_deliverable_status  # type: ignore


def main():
    is_workflow_active = get_state("workflow_active")
    if not is_workflow_active:
        sys.exit(0)
    hook_input = read_stdin_json()
    hook_event_name = hook_input.get("hook_event_name", "")

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    command = tool_input.get("command", "")
    if hook_event_name != "PostToolUse":
        return

    if tool_name not in ["Write", "Edit", "Bash"]:
        return

    value = file_path or command
    print(f"Value: {value}")
    log_deliverable_status(value)


if __name__ == "__main__":
    main()
