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


test = {"tool_input": {"subagent_type": "codebase-explorer"}}


def load_roadmap_data() -> dict | None:
    """Load roadmap once. Returns None if unavailable."""
    version = get_current_version()
    if not version:
        return None
    return load_roadmap(get_roadmap_path(version))


def is_implement_active(cache_key: str) -> bool:
    """Check if codebase explorer is active."""
    return get_cache(cache_key) is True


def main() -> None:
    """Main entry point."""
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    if not is_implement_active("is_implement_active"):
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    subagent = input_data.get("tool_input", {}).get("subagent_type", "")
    last_agent_used = get_cache("last_agent_used")
    if last_agent_used != "codebase-explorer":
        print(f"Dependency violation: {last_agent_used} must be used before {subagent}")
        sys.exit(2)

    if hook_event == "PostToolUse":
        set_cache("last_agent_used", subagent)

    sys.exit(2)


if __name__ == "__main__":
    main()
