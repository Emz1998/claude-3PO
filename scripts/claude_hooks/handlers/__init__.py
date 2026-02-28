"""Handler registry for Claude Code hook dispatchers."""

from typing import Any, Callable

from scripts.claude_hooks.handlers import (
    phase_guard,
    log_guard,
    commit_guard,
    implement_trigger,
    build_entry,
    session_recorder,
    logging_reminder,
    parallel_tasks,
    stop_guard,
)

Handler = Callable[[dict[str, Any]], None]

HANDLER_REGISTRY: dict[str, list[Handler]] = {
    "PreToolUse": [phase_guard.handle, log_guard.handle, commit_guard.handle],
    "PostToolUse": [session_recorder.handle, logging_reminder.handle, parallel_tasks.handle],
    "UserPromptSubmit": [build_entry.handle, implement_trigger.handle],
    "Stop": [stop_guard.handle],
}


def get_handlers(event: str) -> list[Handler]:
    return HANDLER_REGISTRY.get(event, [])
