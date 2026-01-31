#!/usr/bin/env python3
"""SubagentStop hook for workflow enforcement."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json


sys.path.insert(0, str(Path(__file__).parent))
from state import mark_deliverable_complete, get_state  # type: ignore


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

    if tool_name not in ["Write", "Edit", "Bash", "Read"]:
        return

    if tool_name == "Write" or tool_name == "Edit":
        file_path = tool_input.get("file_path", "")
        if not file_path:
            sys.exit(0)

        if tool_name == "Write":
            action = "write"
        elif tool_name == "Edit":
            action = "edit"
        elif tool_name == "Read":
            action = "read"
        else:
            sys.exit(0)
        mark_deliverable_complete(action, file_path)

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if not command:
            sys.exit(0)
        mark_deliverable_complete("bash", command)


if __name__ == "__main__":
    main()
