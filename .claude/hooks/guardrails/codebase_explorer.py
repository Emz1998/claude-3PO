#!/usr/bin/env python3
"""
Engineer task completion guard.

Ensures engineer agents complete their assigned tasks:
- Blocks tools until task is in_progress
- Prevents SubagentStop until task is completed
- Allows log:task skill to update task status
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (  # type: ignore
    block_response,
    get_cache,
    load_cache,
    set_cache,
    read_stdin_json,
    get_current_version,
    get_roadmap_path,
    load_roadmap,
    find_task_in_roadmap,
    log,
)

from roadmap import get_current_phase, get_current_milestone

TODO_FILE_PATH = f"project/{get_current_version()}/{get_current_phase()}/{get_current_milestone()}/todos/todos_{datetime.now().strftime('%Y-%m-%d')}_{get_cache('session_id')}.md"
CACHE_PATH = Path(".claude/hooks/cache/codebase_explorer_cache.json")

test = {
    "hook_event_name": "PreToolUse",
    "tool_name": "Read",
    "tool_input": {
        "file_path": TODO_FILE_PATH,
    },
}


def is_implement_active(cache: dict) -> bool:
    """Check if codebase explorer is active."""
    return get_cache("is_implement_active", cache) is True


def main() -> None:
    """Main entry point."""
    input_data = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {
            "file_path": TODO_FILE_PATH,
        },
    }

    cache = load_cache(CACHE_PATH)
    if not input_data:
        sys.exit(0)

    if not is_implement_active(cache):
        print("Proceeding...")
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    tool_name = input_data.get("tool_name", "")

    if hook_event == "PostToolUse":
        if tool_name == "Task":
            subagent = input_data.get("tool_input", {}).get("subagent_type", "")
            set_cache("last_agent_used", subagent, cache)
        if tool_name == "Read":
            file_path = input_data.get("tool_input", {}).get("file_path", "")
            if TODO_FILE_PATH in file_path:
                set_cache("has_read_todo_file", True, cache)

    if hook_event == "PreToolUse":
        if tool_name == "Task":
            if not get_cache("has_read_todo_file", cache):
                block_response(
                    f"You must read the todo file ({TODO_FILE_PATH}) before using the Task tool."
                )


if __name__ == "__main__":
    main()
