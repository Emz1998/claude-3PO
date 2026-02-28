"""UserPromptSubmit handler — intercepts /implement and starts a story."""

import re
from typing import Any

from scripts.claude_hooks.models import UserPromptSubmit
from scripts.claude_hooks.responses import block
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.handlers.workflow_gate import activate_workflow


def handle(hook_input: dict[str, Any]) -> None:
    """Implement trigger handler."""
    hook = UserPromptSubmit(**hook_input)

    if hook.prompt is None:
        return
    if not hook.prompt.startswith("/implement"):
        return

    parts = hook.prompt.strip().split(" ")
    if len(parts) != 2:
        block("Invalid prompt")
        return

    story_id = parts[1]
    pattern = re.compile(r"^(US|TS|BG|SK)-\d{3}$")
    if not pattern.match(story_id):
        block(
            f"Invalid ID format: '{story_id}'. Expected format like: US-001 or TS-001 or BG-001 or SK-001"
        )
        return

    sprint = Sprint.create()
    activate_workflow()
    ok, error = sprint.start_story(story_id)
    if not ok:
        block(error or "Failed to start story")
        return

    print(f"Started story {story_id}\n")
    print(sprint.render_context(story_id), "\n")
