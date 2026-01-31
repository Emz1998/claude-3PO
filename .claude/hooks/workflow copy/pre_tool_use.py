#!/usr/bin/env python3
"""PreToolUse hook for workflow enforcement. Only runs for main agent."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.state import get_state, is_workflow_active  # type: ignore
from lib.guardrails import load_config, check_subagent_allowed  # type: ignore


def block(reason: str) -> None:
    """Block tool use with reason."""
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def main() -> None:
    input_data = json.load(sys.stdin)

    # Skip if workflow not active
    if not is_workflow_active():
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Block /implement skill from subagents (only main agent can trigger)
    if tool_name == "Skill" and tool_input.get("skill") == "implement":
        # This hook only runs for main agent, so allow it
        sys.exit(0)

    # Enforce subagent restrictions on Task tool
    if tool_name == "Task":
        subagent_type = tool_input.get("subagent_type", "")
        if subagent_type:
            config = load_config("workflow")
            state = get_state()
            allowed, reason = check_subagent_allowed(config, state, subagent_type)
            if not allowed:
                block(reason)

    sys.exit(0)


if __name__ == "__main__":
    main()
