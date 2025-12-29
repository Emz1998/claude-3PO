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
    write_cache,
    read_stdin_json,
    get_current_version,
    get_roadmap_path,
    load_roadmap,
    find_task_in_roadmap,
    log,
)

ENGINEER_AGENTS = {
    "backend-engineer",
    "frontend-engineer",
    "fullstack-developer",
    "html-prototyper",
    "react-prototyper",
    "test-engineer",
}

ALLOWED_SKILLS = {"log:task"}

CACHE_KEY = "engineer_guard_active"
TASK_KEY = "engineer_assigned_task"
AGENT_ID_KEY = "engineer_assigned_agent"
SUBAGENT_TYPE_KEY = "engineer_subagent_type"


def load_roadmap_data() -> dict | None:
    """Load roadmap once. Returns None if unavailable."""
    version = get_current_version()
    if not version:
        return None
    return load_roadmap(get_roadmap_path(version))


def is_active() -> bool:
    """Check if engineer guard is active."""
    return get_cache(CACHE_KEY) is True


def get_assigned_task() -> str | None:
    """Get the assigned task ID from cache."""
    return get_cache(TASK_KEY)


def get_assigned_agent() -> str | None:
    """Get the assigned agent ID from cache."""
    return get_cache(AGENT_ID_KEY)


def get_subagent_type() -> str | None:
    """Get the subagent type from cache."""
    return get_cache(SUBAGENT_TYPE_KEY)


def activate(input_data: dict) -> None:
    """Activate guard and store current task with agent tracking."""
    tool_input = input_data.get("tool_input") or {}
    subagent_type = tool_input.get("subagent_type", "")
    agent_id = input_data.get("tool_use_id", "")

    roadmap = load_roadmap_data()
    task_id = roadmap.get("current", {}).get("task") if roadmap else None

    cache = load_cache()
    cache[CACHE_KEY] = True
    cache[TASK_KEY] = task_id
    cache[AGENT_ID_KEY] = agent_id
    cache[SUBAGENT_TYPE_KEY] = subagent_type
    write_cache(cache)

    log(f"ENGINEER_GUARD: Activated for {subagent_type} (agent={agent_id}, task={task_id})")


def deactivate() -> None:
    """Deactivate guard and clear all assigned values."""
    subagent_type = get_subagent_type()
    task_id = get_assigned_task()

    cache = load_cache()
    cache[CACHE_KEY] = False
    cache[TASK_KEY] = None
    cache[AGENT_ID_KEY] = None
    cache[SUBAGENT_TYPE_KEY] = None
    write_cache(cache)

    log(f"ENGINEER_GUARD: Deactivated for {subagent_type} (task={task_id})")


def is_build_active() -> bool:
    """Check if /build skill is active."""
    return get_cache("build_skill_active") is True


def get_task_for_check() -> tuple[str | None, str | None]:
    """Get task ID and status with single roadmap load.

    Uses assigned task from cache to prevent race condition where
    roadmap advances after task completion but before stop.
    Falls back to current task if cache is empty.
    Returns (None, None) when state can't be verified - fails open.
    """
    roadmap = load_roadmap_data()
    if not roadmap:
        log("ENGINEER_GUARD: Failing open - roadmap unavailable")
        return None, None

    task_id = get_assigned_task()
    if not task_id:
        task_id = roadmap.get("current", {}).get("task")

    if not task_id:
        log("ENGINEER_GUARD: Failing open - no task ID found")
        return None, None

    _, _, task = find_task_in_roadmap(roadmap, task_id)
    if not task:
        log(f"ENGINEER_GUARD: Failing open - task '{task_id}' not in roadmap")
        return None, None

    return task_id, task.get("status", "not_started")


def handle_pretool(input_data: dict) -> None:
    """Handle PreToolUse event."""
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input") or {}

    # Task spawn - activate guard for engineer agents
    if tool_name == "Task":
        subagent = tool_input.get("subagent_type", "")
        if subagent in ENGINEER_AGENTS:
            activate(input_data)
        return

    if not is_active():
        return

    task_id, status = get_task_for_check()

    # No task found - allow through (graceful degradation)
    if not task_id:
        return

    # Task completed - agent should stop
    if status == "completed":
        block_response(
            f"GUARD: Task '{task_id}' is completed. Stop working and return results."
        )

    # Allow specific skills through for status updates
    if tool_name == "Skill" and tool_input.get("skill") in ALLOWED_SKILLS:
        return

    # Block if task not in_progress
    if status != "in_progress":
        block_response(
            f"GUARD: Task '{task_id}' must be 'in_progress' first (current: '{status}'). "
            f"Use: /log:task {task_id} in_progress"
        )


def handle_stop(_input_data: dict) -> None:
    """Handle SubagentStop event."""
    if not is_active():
        return

    task_id, status = get_task_for_check()

    # No task found - allow stop and cleanup
    if not task_id:
        deactivate()
        return

    # Task completed - allow stop and cleanup
    if status == "completed":
        deactivate()
        return

    # Block stop - guard remains active until task completes
    block_response(
        f"GUARD: Cannot stop. Task '{task_id}' must be 'completed' "
        f"(current: '{status}'). Use: /log:task {task_id} completed"
    )


def main() -> None:
    """Main entry point."""
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    if not is_build_active():
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")

    if hook_event == "PreToolUse":
        handle_pretool(input_data)
    elif hook_event == "SubagentStop":
        handle_stop(input_data)

    sys.exit(0)


if __name__ == "__main__":
    main()
