#!/usr/bin/env python3
"""
Context injection hook for engineer subagents.

Injects task logging workflow reminders when spawning engineer subagents.
Uses PreToolUse with Task matcher to add context about log:task and log:ac usage.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (  # type: ignore
    read_stdin_json,
    get_cache,
    add_context,
)

# Engineer agents that need task logging reminders
ENGINEER_AGENTS = {
    "backend-engineer",
    "frontend-engineer",
    "fullstack-developer",
    "html-prototyper",
    "react-prototyper",
    "test-engineer",
}

TASK_LOGGING_CONTEXT = """
## Task Logging Workflow (REQUIRED)

Before starting work:
1. Call `/log:task <task-id> in_progress` to mark task as in progress

Before completing task:
2. Call `/log:ac <ac-id> met` for each acceptance criteria that is met

After all ACs are met:
3. Call `/log:task <task-id> completed` to mark task as completed

**Important:** You cannot complete a task until all its acceptance criteria are marked as "met".
"""


def is_build_active() -> bool:
    """Check if /build skill is currently active."""
    return get_cache("build_skill_active") is True


def main() -> None:
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    # Only run when /build skill is active
    if not is_build_active():
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    tool_name = input_data.get("tool_name", "")

    # Only handle PreToolUse for Task tool
    if hook_event != "PreToolUse" or tool_name != "Task":
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    subagent_type = tool_input.get("subagent_type", "")

    # Only inject context for engineer agents
    if subagent_type not in ENGINEER_AGENTS:
        sys.exit(0)

    # Add task logging workflow context (PreToolUse uses systemMessage)
    add_context(TASK_LOGGING_CONTEXT, "PreToolUse")


if __name__ == "__main__":
    main()
