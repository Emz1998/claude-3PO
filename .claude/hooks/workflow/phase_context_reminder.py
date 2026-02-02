#!/usr/bin/env python3
"""PostToolUse hook for injecting phase-specific context reminders."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json, add_context  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from state import get_state  # type: ignore
from phase_reminders import get_phase_reminder  # type: ignore


def main():
    # Check if workflow is active
    is_workflow_active = get_state("workflow_active")
    if not is_workflow_active:
        sys.exit(0)

    # Read hook input
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    hook_event_name = hook_input.get("hook_event_name", "")
    if hook_event_name != "PostToolUse":
        sys.exit(0)

    # Filter for Skill tool only
    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Skill":
        sys.exit(0)

    # Get phase from skill name
    tool_input = hook_input.get("tool_input", {})
    skill_name = tool_input.get("skill", "")
    if not skill_name:
        sys.exit(0)

    # Get phase reminder content
    reminder = get_phase_reminder(skill_name)
    if not reminder:
        sys.exit(0)

    # Inject reminder via add_context
    add_context(reminder, "PostToolUse")


if __name__ == "__main__":
    main()
