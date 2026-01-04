#!/usr/bin/env python3
"""PostToolUse hook to detect when todo file is read.

When Read tool is used on a todo file matching the pattern:
  project/{version}/{phase}/{milestone}/todos/todos_{date}_{session_id}.md

And the workflow is in IMPLEMENT_ACTIVE state:
- Transitions to TODO_READ state
- Stores the todo file path in cache
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json  # type: ignore
from workflow.implement_state import (  # type: ignore
    is_workflow_active,
    get_current_state,
    set_todo_read,
    STATE_IMPLEMENT_ACTIVE,
)

# Pattern to match todo file paths
# Matches both: project/{version}/todos/todo_{date}_{session}.md
# and: project/{version}/{phase}/{milestone}/todos/todos_{date}_{session}.md
TODO_PATH_PATTERN = re.compile(
    r"project/[^/]+(?:/[^/]+)*/todos/todos?_\d{4}-\d{2}-\d{2}_[\w-]+\.md$"
)


def is_todo_file(file_path: str) -> bool:
    """Check if file path matches todo file pattern."""
    return bool(TODO_PATH_PATTERN.search(file_path))


def main() -> None:
    """Check if Read tool was used on todo file and update state."""
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    if hook_event != "PostToolUse":
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Read":
        sys.exit(0)

    # Only process if workflow is active and in IMPLEMENT_ACTIVE state
    if not is_workflow_active():
        sys.exit(0)

    if get_current_state() != STATE_IMPLEMENT_ACTIVE:
        sys.exit(0)

    # Get file path from tool input
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if file_path and is_todo_file(file_path):
        # Transition to TODO_READ state
        set_todo_read(file_path)

    sys.exit(0)


if __name__ == "__main__":
    main()
