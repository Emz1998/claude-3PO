#!/usr/bin/env python3
"""
Codebase explorer dependency guard.

Ensures dependencies are met before allowing Task tool usage:
1. implement skill must be triggered and active
2. The todo file must be read first

Tracks state via PostToolUse events and blocks PreToolUse when deps unmet.
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
    log,
)

from roadmap import get_current_phase_full_name, get_current_milestone_full_name  # type: ignore

CACHE_PATH = Path(".claude/hooks/cache/codebase_explorer_cache.json")

test_input_data: dict = {
    "hook_event_name": "PostToolUse",
    "tool_name": "Read",
    "tool_input": {
        "file_path": f"/home/emhar/.claude/projects/{get_current_version()}/{get_current_phase_full_name()}/{get_current_milestone_full_name()}/todos/todos_{datetime.now().strftime("%Y-%m-%d")}_{get_cache("session_id")}.md",
    },
}


def get_todo_file_path() -> str:
    """Generate the todo file path for current session."""
    version = get_current_version()
    phase = get_current_phase_full_name()
    milestone = get_current_milestone_full_name()
    session_id = get_cache("session_id")
    date_str = datetime.now().strftime("%Y-%m-%d")
    absolute_path = Path(".claude/projects").absolute()
    print(absolute_path)
    return f"/home/emhar/.claude/projects/{version}/{phase}/{milestone}/todos/todos_{date_str}_{session_id}.md"


def is_implement_active(cache: dict) -> bool:
    """Check if implement skill is triggered and active."""
    return cache.get("is_implement_active", False)


def has_read_todo_file(cache: dict) -> bool:
    """Check if todo file has been read."""
    return cache.get("has_read_todo_file") is True


def check_dependencies(cache: dict) -> tuple[bool, str]:
    """
    Check if all dependencies are met.

    Returns:
        tuple[bool, str]: (all_met, error_message)
    """
    todo_path = get_todo_file_path()

    # Dependency 1: implement must be active
    if not is_implement_active(cache):
        return False, "DEPENDENCY: implement skill must be triggered first."

    # Dependency 2: todo file must be read
    if not has_read_todo_file(cache):
        return (
            False,
            f"DEPENDENCY: You must read the todo file ({todo_path}) before using the Task tool.",
        )

    return True, ""


def handle_post_tool_use(tool_name: str, tool_input: dict, cache: dict) -> None:
    """Track state after tool execution."""
    todo_path = get_todo_file_path()

    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        # Check if the read file matches the todo file path
        if file_path == todo_path:
            cache["has_read_todo_file"] = True
            set_cache("has_read_todo_file", True)
            log(f"[codebase_explorer] Todo file read: {file_path}")

    if tool_name == "Task":
        subagent = tool_input.get("subagent_type", "")
        cache["last_agent_used"] = subagent
        set_cache("last_agent_used", subagent)


def handle_pre_tool_use(tool_name: str, tool_input: dict, cache: dict) -> None:
    """Check dependencies before tool execution."""
    # Only check dependencies for Task tool
    if tool_name != "Task":
        return

    deps_met, error_msg = check_dependencies(cache)
    if not deps_met:
        block_response(error_msg)


def main() -> None:
    """Main entry point."""
    input_data = test_input_data
    cache = load_cache(CACHE_PATH)

    # Skip if implement is not active (this hook only applies during /implement workflow)
    if not is_implement_active(cache):
        print("Implement is not active")
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if hook_event == "PostToolUse":
        handle_post_tool_use(tool_name, tool_input, cache)

    elif hook_event == "PreToolUse":
        handle_pre_tool_use(tool_name, tool_input, cache)

    sys.exit(0)


if __name__ == "__main__":
    main()
