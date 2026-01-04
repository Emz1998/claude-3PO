#!/usr/bin/env python3
"""PostToolUse tracker for /implement workflow progression.

When Task tool completes for controlled subagents:
- Advances workflow state based on which subagent completed
- Handles transitions through pre-coding and coding phases
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json, load_cache, write_cache  # type: ignore
from workflow.implement_state import (  # type: ignore
    is_workflow_active,
    get_current_state,
    set_state,
    advance_coding_step,
    start_coding_phase,
    is_in_coding_phase,
    STATE_TODO_READ,
    STATE_EXPLORER_DONE,
    STATE_PLANNER_DONE,
    STATE_CONSULTANT_DONE,
)

# Mapping of subagent types to the state they transition TO after completion
SUBAGENT_STATE_TRANSITIONS = {
    # Pre-coding phase
    "codebase-explorer": STATE_EXPLORER_DONE,
    "planning-specialist": STATE_PLANNER_DONE,
    "plan-consultant": STATE_CONSULTANT_DONE,
}

# Subagents in the coding phase (handled differently)
CODING_PHASE_SUBAGENTS = {
    "test-engineer",
    "frontend-engineer",
    "backend-engineer",
    "fullstack-developer",
    "version-manager",
    "code-reviewer",
}


def main() -> None:
    """Track subagent completion and advance workflow state."""
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    if hook_event != "PostToolUse":
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Task":
        sys.exit(0)

    # Only process if workflow is active
    if not is_workflow_active():
        sys.exit(0)

    # Get subagent type from tool input
    tool_input = input_data.get("tool_input", {})
    subagent_type = tool_input.get("subagent_type", "")

    # Check tool response for completion status
    tool_response = input_data.get("tool_response", {})
    status = tool_response.get("status", "")

    # Only advance on successful completion
    if status != "completed":
        sys.exit(0)

    current_state = get_current_state()

    # Handle pre-coding phase transitions
    if subagent_type in SUBAGENT_STATE_TRANSITIONS:
        next_state = SUBAGENT_STATE_TRANSITIONS[subagent_type]
        set_state(next_state)

        # After plan-consultant completes (CONSULTANT_DONE), start coding phase
        if next_state == STATE_CONSULTANT_DONE:
            start_coding_phase()

        sys.exit(0)

    # Handle coding phase subagents
    if subagent_type in CODING_PHASE_SUBAGENTS:
        if is_in_coding_phase():
            # Advance to next coding step
            advance_coding_step()

    sys.exit(0)


if __name__ == "__main__":
    main()
