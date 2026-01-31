#!/usr/bin/env python3
"""PreToolUse guardrail for /implement workflow subagent ordering.

Ensures subagents are triggered in the correct order:
1. codebase-explorer (requires TODO_READ state)
2. planning-specialist (requires EXPLORER_DONE state)
3. plan-consultant (requires PLANNER_DONE state)
4. Then coding workflow based on TDD/TA/DEFAULT mode

Blocks subagent execution (exit 2) if triggered out of order.
Uses task owner from roadmap.json to determine expected engineer subagent.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json, block_response  # type: ignore
from workflow.implement_state import (  # type: ignore
    is_workflow_active,
    get_current_state,
    get_expected_subagent_for_state,
)
from roadmap.utils import get_current_task, get_task_owner  # type: ignore

# Subagents controlled by this guardrail (planning + coding phases)
PLANNING_SUBAGENTS = {
    "codebase-explorer",
    "planning-specialist",
    "plan-consultant",
}

CODING_SUBAGENTS = {
    "test-engineer",
    "frontend-engineer",
    "backend-engineer",
    "fullstack-developer",
    "version-manager",
    "code-reviewer",
}

# Combined set for quick membership check
CONTROLLED_SUBAGENTS = PLANNING_SUBAGENTS | CODING_SUBAGENTS

# Valid engineer subagent names that can be task owners
ENGINEER_SUBAGENTS = {
    "frontend-engineer",
    "backend-engineer",
    "fullstack-developer",
}

# Default engineers when task owner is "main-agent" or not specific
DEFAULT_ENGINEER_SUBAGENTS = [
    "frontend-engineer",
    "backend-engineer",
    "fullstack-developer",
]

# States that expect an engineer subagent
ENGINEER_EXPECTED_STATES = {
    "CODING_TDD_3",
    "CODING_TA_1",
    "CODING_DEFAULT_1",
}

# Human-readable state names for error messages
STATE_DESCRIPTIONS = {
    "IDLE": "workflow not active",
    "IMPLEMENT_ACTIVE": "waiting for todo file to be read",
    "TODO_READ": "ready for codebase explorer",
    "EXPLORER_DONE": "ready for planner",
    "PLANNER_DONE": "ready for plan consultant",
    "CONSULTANT_DONE": "ready for coding phase",
    "CODING_TDD_1": "TDD: waiting for test engineer to create failing tests",
    "CODING_TDD_2": "TDD: waiting for version manager to commit tests",
    "CODING_TDD_3": "TDD: waiting for engineer to implement",
    "CODING_TDD_4": "TDD: waiting for code reviewer",
    "CODING_TDD_5": "TDD: waiting for version manager to commit",
    "CODING_TA_1": "TA: waiting for engineer to implement",
    "CODING_TA_2": "TA: waiting for test engineer",
    "CODING_TA_3": "TA: waiting for code reviewer",
    "CODING_TA_4": "TA: waiting for version manager to commit",
    "CODING_DEFAULT_1": "Default: waiting for engineer to implement",
    "CODING_DEFAULT_2": "Default: waiting for code/QA reviewer",
    "CODING_DEFAULT_3": "Default: waiting for version manager to commit",
}


def get_state_description(state: str) -> str:
    """Get human-readable description of a state."""
    return STATE_DESCRIPTIONS.get(state, f"state: {state}")


def main() -> None:
    """Guard subagent execution based on workflow state."""
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    if hook_event != "PreToolUse":
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Task":
        sys.exit(0)

    # Get subagent type from tool input
    tool_input = input_data.get("tool_input", {})
    subagent_type = tool_input.get("subagent_type", "")

    # Only guard controlled subagents
    if subagent_type not in CONTROLLED_SUBAGENTS:
        sys.exit(0)

    # If workflow is not active, allow all subagents (not in /implement context)
    if not is_workflow_active():
        sys.exit(0)

    # Get current state and expected subagents
    current_state = get_current_state()
    expected_subagents = get_expected_subagent_for_state(current_state)

    # Check if subagent is allowed in current state
    if subagent_type in expected_subagents:
        # Allowed - let it proceed
        sys.exit(0)

    # Not allowed - block with informative error
    state_desc = get_state_description(current_state)

    if expected_subagents:
        expected_str = ", ".join(expected_subagents)
        block_response(
            f"Workflow guardrail: Cannot trigger '{subagent_type}' now. "
            f"Current state: {state_desc}. "
            f"Expected subagent(s): {expected_str}"
        )
    else:
        block_response(
            f"Workflow guardrail: Cannot trigger '{subagent_type}' now. "
            f"Current state: {state_desc}. "
            f"No subagent expected at this state."
        )


if __name__ == "__main__":
    main()
