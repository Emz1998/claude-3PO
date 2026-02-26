#!/usr/bin/env python3
"""PostToolUse reminder — suggests parallel-ready tasks after a single-task log."""

from typing import Any

from scripts.claude_hooks.utils.hook import PostToolUse, Skill  # type: ignore
from scripts.claude_hooks.sprint.sprint import Sprint  # type: ignore


class ParallelTasksReminder:
    """After a successful `/log task <id> in_progress`, remind about parallel-ready tasks."""

    def __init__(self, hook_input: dict[str, Any]):
        self._hook = PostToolUse(**hook_input)
        self._sprint = Sprint.create()

    def run(self) -> None:
        if not isinstance(self._hook.tool_input, Skill):
            return
        if self._hook.tool_input.skill != "log":
            return
        if not self._hook.tool_input.args:
            return

        args = self._hook.tool_input.args.strip().split()
        if len(args) != 3:
            return

        ticket_type, raw_ids, status = args
        if ticket_type != "task" or status != "in_progress":
            return

        logged_ids = {tid.strip() for tid in raw_ids.split("|") if tid.strip()}
        ready = self._sprint.task.get_ready_tasks()
        remaining = [t for t in ready if t not in logged_ids]
        if not remaining:
            return

        piped = "|".join(remaining)
        print(
            f"Tip: {', '.join(remaining)} can also run in parallel. Use: /log task {piped} in_progress"
        )


if __name__ == "__main__":
    from scripts.claude_hooks.utils.hook import Hook  # type: ignore

    hook_input = Hook._read_stdin()
    ParallelTasksReminder(hook_input).run()
