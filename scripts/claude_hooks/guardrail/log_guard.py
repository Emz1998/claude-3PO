#!/usr/bin/env python3
"""PreToolUse guard for /log skill — validates args and updates sprint state."""

import re
from typing import Any, Callable

from scripts.claude_hooks.utils.hook import PreToolUse, Skill  # type: ignore
from scripts.claude_hooks.sprint.sprint import Sprint  # type: ignore

VALID_STATUSES = {"in_progress", "completed"}
TICKET_PATTERNS = {
    "task": re.compile(r"^T-\d{3}$"),
    "story": re.compile(r"^(TS|SK|US|BG)-\d{3}$"),
}


class LogGuard:
    """Intercepts `skill:log` calls, validates args, and updates sprint state."""

    def __init__(self, hook_input: dict[str, Any]):
        self._hook = PreToolUse(**hook_input)
        self._sprint = Sprint.create()

    def run(self) -> None:
        if not isinstance(self._hook.tool_input, Skill):
            return
        if self._hook.tool_input.skill != "log":
            return
        if not self._hook.tool_input.args:
            self._hook.block("Usage: /log <type> <ticket_id> <status>")
            return

        args = self._hook.tool_input.args.strip().split()
        if len(args) != 3:
            self._hook.block("Expected 3 args: <type> <ticket_id> <status>")
            return

        ticket_type, raw_ids, status = args

        if ticket_type not in TICKET_PATTERNS:
            self._hook.block(f"Invalid type '{ticket_type}'. Use: task, story")
            return

        if status not in VALID_STATUSES:
            self._hook.block(f"Invalid status '{status}'. Use: in_progress, completed")
            return

        ticket_ids = [tid.strip() for tid in raw_ids.split("|") if tid.strip()]
        pattern = TICKET_PATTERNS[ticket_type]
        for tid in ticket_ids:
            if not pattern.match(tid):
                expected = "T-XXX" if ticket_type == "task" else "(TS|SK|US|BG)-XXX"
                self._hook.block(
                    f"Invalid {ticket_type} ID '{tid}'. Expected: {expected}"
                )
                return

        # Preflight: verify all IDs can transition before applying any
        error = self._preflight(ticket_type, ticket_ids, status)
        if error:
            self._hook.block(error)
            return

        # Apply all transitions
        actions: dict[tuple[str, str], Callable[..., tuple[bool, str]]] = {
            ("task", "in_progress"): self._sprint.start_task,
            ("task", "completed"): self._sprint.complete_task,
            ("story", "in_progress"): self._sprint.start_story,
            ("story", "completed"): self._sprint.complete_story,
        }
        action = actions[(ticket_type, status)]
        for tid in ticket_ids:
            action(tid)
            print(f"Updated {ticket_type} {tid} -> {status}")

    def _preflight(
        self, ticket_type: str, ticket_ids: list[str], status: str
    ) -> str | None:
        """Validate all IDs can transition. Returns error message or None."""
        if ticket_type == "task" and not self._sprint.state.current_story:
            return "No active story. Start a story before logging tasks."

        if ticket_type == "task":
            story = self._sprint.state.current_story
            tasks = self._sprint.state.tasks
            if tasks.get(story) is None:
                return f"Story '{story}' not found"
            bucket = tasks[story]
            for tid in ticket_ids:
                if status == "in_progress":
                    if tid in bucket.in_progress:
                        return f"Task '{tid}' is already in progress"
                    if tid in bucket.completed:
                        return f"Task '{tid}' is already completed"
                    if tid not in bucket.ready:
                        return f"Task '{tid}' is not in ready"
                else:
                    if tid not in bucket.in_progress:
                        return f"Task '{tid}' must be in progress before completing"
        return None


if __name__ == "__main__":
    from scripts.claude_hooks.utils.hook import Hook  # type: ignore

    hook_input = Hook._read_stdin()
    LogGuard(hook_input).run()
