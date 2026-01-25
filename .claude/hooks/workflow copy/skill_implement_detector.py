#!/usr/bin/env python3
"""PreToolUse hook to detect implement skill invocation.

When the Skill tool is called with skill="implement" or "build":
- Activates the implement workflow state machine
- Resets to IMPLEMENT_ACTIVE state
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json  # type: ignore
from workflow.implement_state import activate_workflow  # type: ignore

# Skill names that activate the implement workflow
IMPLEMENT_SKILLS = {"implement", "build"}


def main() -> None:
    """Check if Skill tool is called with implement and activate workflow."""
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    if hook_event != "PreToolUse":
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Skill":
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    skill_name = tool_input.get("skill", "").lower()

    # Check if skill matches implement patterns
    if skill_name in IMPLEMENT_SKILLS:
        # Activate the workflow (resets state to IMPLEMENT_ACTIVE)
        activate_workflow()

    sys.exit(0)


if __name__ == "__main__":
    main()
