#!/usr/bin/env python3
# Engineer Task Logger Guardrail
# Blocks tools until current task is in_progress, prevents stop until completed

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (  # type: ignore
    GuardrailConfig,
    GuardrailRunner,
    block_response,
    get_cache,
    load_cache,
    write_cache,
    get_current_version,
    get_roadmap_path,
    load_roadmap,
    find_task_in_roadmap,
)

ENGINEER_AGENTS = {
    "backend-engineer",
    "frontend-engineer",
    "fullstack-developer",
    "html-prototyper",
    "react-prototyper",
    "test-engineer",
}


def get_current_task_status() -> tuple[str | None, str | None]:
    """Get current task ID and status from roadmap. Returns (task_id, status)."""
    version = get_current_version()
    if not version:
        return None, None

    roadmap_path = get_roadmap_path(version)
    roadmap = load_roadmap(roadmap_path)
    if not roadmap:
        return None, None

    current = roadmap.get("current", {})
    task_id = current.get("task")
    if not task_id:
        return None, None

    _, _, task = find_task_in_roadmap(roadmap, task_id)
    if not task:
        return task_id, None

    return task_id, task.get("status", "not_started")


class EngineerTaskLoggerRunner(GuardrailRunner):
    """Extended runner that checks roadmap status for task progression."""

    def __init__(self, config: GuardrailConfig):
        super().__init__(config)

    def handle_task_pretool(self, input_data: dict) -> None:
        """Activate guardrail when any engineer subagent is spawned."""
        tool_input = input_data.get("tool_input", {})
        subagent_type = tool_input.get("subagent_type", "")
        if subagent_type in ENGINEER_AGENTS:
            self.activate()

    def handle_tool_pretool(self, input_data: dict) -> None:
        if not self.is_active():
            return

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Allow log:task skill to pass through
        if tool_name == "Skill":
            skill_name = tool_input.get("skill", "")
            if skill_name == "log:task":
                return

        # Check current task status from roadmap
        task_id, status = get_current_task_status()

        if status != "in_progress":
            block_response(
                f"GUARDRAIL: {tool_name} blocked. "
                f"Current task '{task_id}' must be 'in_progress' first (current: '{status}'). "
                "Use: /log:task <task-id> in_progress"
            )

    def handle_subagent_stop(self, input_data: dict) -> None:
        if not self.is_active():
            return

        # Check if current task is completed
        task_id, status = get_current_task_status()

        if status != "completed":
            # Output continue: true to prevent stoppage
            print(json.dumps({"continue": True}))
            print(
                f"GUARDRAIL: Cannot stop. Task '{task_id}' must be 'completed' first "
                f"(current: '{status}'). Use: /log:task <task-id> completed",
                file=sys.stderr
            )
            sys.exit(0)

        # Task is completed, allow stop and deactivate
        self.deactivate()

    def run(self) -> None:
        from utils import read_stdin_json  # type: ignore

        input_data = read_stdin_json()
        if not input_data:
            sys.exit(0)

        hook_event = input_data.get("hook_event_name", "")
        tool_name = input_data.get("tool_name", "")

        if hook_event == "PreToolUse":
            if tool_name == "Task":
                self.handle_task_pretool(input_data)
            else:
                self.handle_tool_pretool(input_data)
        elif hook_event == "SubagentStop":
            self.handle_subagent_stop(input_data)

        sys.exit(0)


config = GuardrailConfig(
    target_subagent="engineer-agents",
    cache_key="engineer_task_logger_guardrail_active",
)

if __name__ == "__main__":
    EngineerTaskLoggerRunner(config).run()
