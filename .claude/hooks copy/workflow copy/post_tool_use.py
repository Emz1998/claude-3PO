#!/usr/bin/env python3
"""PostToolUse hook for workflow state tracking."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.state import (  # type: ignore
    get_state,
    is_workflow_active,
    activate_workflow,
    record_tool_use,
    record_subagent,
    record_deliverable,
)
from lib.guardrails import load_config, check_deliverable_met  # type: ignore

TRIGGER_SKILL = "implement"


def main() -> None:
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Check if "implement" skill triggered - activate workflow
    if tool_name == "Skill" and tool_input.get("skill") == TRIGGER_SKILL:
        activate_workflow()
        sys.exit(0)

    # Skip workflow tracking if not active
    if not is_workflow_active():
        sys.exit(0)

    config = load_config()
    state = get_state()

    # Record tool usage
    record_tool_use(tool_name, tool_input)

    # Record subagent if Task tool
    if tool_name == "Task":
        subagent_type = tool_input.get("subagent_type", "")
        if subagent_type:
            record_subagent(subagent_type)

    # Check if deliverable was met
    met, deliverable_name = check_deliverable_met(config, state, tool_name, tool_input)
    if met and deliverable_name:
        record_deliverable(deliverable_name)

    sys.exit(0)


if __name__ == "__main__":
    main()
