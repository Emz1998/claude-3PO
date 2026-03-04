"""PostToolUse handler — blocks tools if no task is in progress."""

from pathlib import Path
from typing import Any

from scripts.claude_hooks.models import PreToolUse, Skill
from scripts.claude_hooks.responses import block
from scripts.claude_hooks.state_store import StateStore
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.handlers.workflow_gate import check_workflow_gate

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


def handle(hook_input: dict[str, Any]) -> None:
    """Logging reminder handler."""
    if not check_workflow_gate():
        return
    # This handler uses PreToolUse model even though it's registered on PostToolUse
    # because it checks if tools should be blocked before more work happens
    hook = PreToolUse(**hook_input)
    tool_input = hook.tool_input

    if hook.hook_event_name != "PreToolUse":
        return

    if isinstance(tool_input, Skill) and tool_input.skill == "log":
        print("Logging")
        return

    sprint = Sprint.create()
    if sprint.task.no_tasks_in_progress():
        content = (
            f"No tasks logged in progress. Please choose a task to work first.\n"
            f"Pending tasks: {sprint.task.get_pending_tasks()}\n"
            f"Ready tasks: {sprint.task.get_ready_tasks()}\n"
        )
        block(content)
