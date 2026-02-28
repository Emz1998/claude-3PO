"""Stop handler — blocks stoppage when the current story is not completed."""

import sys
from typing import Any

from scripts.claude_hooks.models import Stop
from scripts.claude_hooks.responses import block
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.handlers.workflow_gate import check_workflow_gate


def handle(hook_input: dict[str, Any]) -> None:
    """Stop guard handler."""
    if not check_workflow_gate():
        return
    Stop(**hook_input)  # validate input

    sprint = Sprint.create()
    current = sprint.state.current_story
    if not current:
        print("No current story. Stopping.")
        sys.exit(0)

    if current in sprint.state.stories.completed:
        print(f"Story '{current}' is completed. Stopping.")
        sys.exit(0)

    block(
        f"STOP BLOCKED: Story '{current}' is not completed. "
        "Finish the current story before stopping."
    )
