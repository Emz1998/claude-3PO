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

from typing import Any, cast
from pathlib import Path
from datetime import datetime
from scripts.claude_hooks.utils.state_store import StateStore  # type: ignore
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.project.paths import ProjectPaths
from scripts.claude_hooks.utils.hook import PreToolUse, Skill, Write, Read, Hook


CODING_FILE_EXTENSIONS = (
    ".py",
    ".ts",
    ".js",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".json",
    ".yaml",
    ".yml",
)

CWD = Path.cwd() / ".claude/tmp"


class LoggingReminder:
    """Phase transition guard."""

    def __init__(self, hook_input: dict[str, Any]):
        """Initialize the guard."""
        self._sprint = Sprint.create()
        self._hook = PreToolUse(**hook_input)
        self._flag_file_path = CWD / f"flag_{self._hook.session_id}.json"
        self._state = StateStore(self._flag_file_path)

    def _no_tasks_in_progress(self) -> bool:
        """Check if no tasks are in progress."""
        return self._sprint.task.no_tasks_in_progress()

    @staticmethod
    def check_code_file(file_path: str) -> bool:
        """Check if all coding files are logged."""
        if file_path.endswith(CODING_FILE_EXTENSIONS):
            return True
        return False

    def delete_flag_file(self) -> None:
        """Delete the flag file."""
        self._flag_file_path.unlink()

    def run(self) -> None:
        """Run the test."""
        pre_tool_activated = self._hook.hook_event_name == "PreToolUse"
        tool_input = self._hook.tool_input

        if not pre_tool_activated:
            return

        if isinstance(tool_input, (Skill)) and tool_input.skill == "log":
            print("Logging")
            return

        if self._no_tasks_in_progress():
            content = f"No tasks logged in progress. Please choose a task to work first.\nPending tasks: {self._sprint.task.get_pending_tasks()}\nReady tasks: {self._sprint.task.get_ready_tasks()}\n"
            self._hook.block(content)
            return
