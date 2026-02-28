"""PostToolUse handler — suggests parallel-ready tasks after a single-task log."""

from typing import Any

from scripts.claude_hooks.models import PostToolUse, Skill
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.handlers.workflow_gate import check_workflow_gate


def handle(hook_input: dict[str, Any]) -> None:
    """Parallel tasks reminder handler."""
    if not check_workflow_gate():
        return
    hook = PostToolUse(**hook_input)
    if not isinstance(hook.tool_input, Skill):
        return
    if hook.tool_input.skill != "log":
        return
    if not hook.tool_input.args:
        return

    args = hook.tool_input.args.strip().split()
    if len(args) != 3:
        return

    ticket_type, raw_ids, status = args
    if ticket_type != "task" or status != "in_progress":
        return

    sprint = Sprint.create()
    logged_ids = {tid.strip() for tid in raw_ids.split("|") if tid.strip()}
    ready = sprint.task.get_ready_tasks()
    remaining = [t for t in ready if t not in logged_ids]
    if not remaining:
        return

    piped = "|".join(remaining)
    print(
        f"Tip: {', '.join(remaining)} can also run in parallel. Use: /log task {piped} in_progress"
    )
