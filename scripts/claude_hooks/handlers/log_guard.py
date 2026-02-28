"""PreToolUse handler — validates /log skill args and updates sprint state."""

import re
from typing import Any, Callable

from scripts.claude_hooks.models import PreToolUse, Skill
from scripts.claude_hooks.responses import block, debug
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.handlers.workflow_gate import check_workflow_gate

VALID_STATUSES = {"in_progress", "completed"}
TICKET_PATTERNS = {
    "task": re.compile(r"^T-\d{3}$"),
    "story": re.compile(r"^(TS|SK|US|BG)-\d{3}$"),
}


def _preflight(
    sprint: Sprint, ticket_type: str, ticket_ids: list[str], status: str
) -> str | None:
    """Validate all IDs can transition. Returns error message or None."""
    if ticket_type == "task" and not sprint.state.current_story:
        return "No active story. Start a story before logging tasks."

    if ticket_type == "task":
        story = sprint.state.current_story
        tasks = sprint.state.tasks
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


def handle(hook_input: dict[str, Any]) -> None:
    """Log guard handler."""
    if not check_workflow_gate():
        return
    hook = PreToolUse(**hook_input)
    if not isinstance(hook.tool_input, Skill):
        return
    if hook.tool_input.skill != "log":
        debug(f"not a log skill: {hook.tool_input.skill}")
        return

    if not hook.tool_input.args:
        # block("Usage: /log <type> <ticket_id> <status>")
        debug("Usage: /log <type> <ticket_id> <status>")
        return

    args = hook.tool_input.args.strip().split()
    if len(args) != 3:
        # block("Expected 3 args: <type> <ticket_id> <status>")
        debug("Expected 3 args: <type> <ticket_id> <status>")
        return

    ticket_type, raw_ids, status = args

    if ticket_type not in TICKET_PATTERNS:
        # block(f"Invalid type '{ticket_type}'. Use: task, story")
        debug(f"Invalid type '{ticket_type}'. Use: task, story")
        return

    if status not in VALID_STATUSES:
        # block(f"Invalid status '{status}'. Use: in_progress, completed")
        debug(f"Invalid status '{status}'. Use: in_progress, completed")
        return

    ticket_ids = [tid.strip() for tid in raw_ids.split("|") if tid.strip()]
    pattern = TICKET_PATTERNS[ticket_type]
    for tid in ticket_ids:
        if not pattern.match(tid):
            expected = "T-XXX" if ticket_type == "task" else "(TS|SK|US|BG)-XXX"
            # block(f"Invalid {ticket_type} ID '{tid}'. Expected: {expected}")
            debug(f"Invalid {ticket_type} ID '{tid}'. Expected: {expected}")
            return

    sprint = Sprint.create()

    error = _preflight(sprint, ticket_type, ticket_ids, status)
    if error:
        # block(error)
        debug(error)
        return

    actions: dict[tuple[str, str], Callable[..., tuple[bool, str]]] = {
        ("task", "in_progress"): sprint.start_task,
        ("task", "completed"): sprint.complete_task,
        ("story", "in_progress"): sprint.start_story,
        ("story", "completed"): sprint.complete_story,
    }
    action = actions[(ticket_type, status)]
    for tid in ticket_ids:
        action(tid)
        print(f"Updated {ticket_type} {tid} -> {status}")
