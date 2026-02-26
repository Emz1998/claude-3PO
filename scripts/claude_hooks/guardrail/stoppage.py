#!/usr/bin/env python3
"""Stop guard: blocks stoppage when the current story is not completed."""

import sys
from typing import Any
from scripts.claude_hooks.sprint.sprint import Sprint  # type: ignore
from scripts.claude_hooks.utils.hook import Stop


class StopGuard:

    def __init__(self, hook_input: dict[str, Any]):
        self._hook = Stop(**hook_input)

    def run(self) -> None:
        sprint = Sprint.create()
        current = sprint.state.current_story
        if not current:
            print("No current story. Stopping.")
            sys.exit(0)

        if current in sprint.state.stories.completed:
            print(f"Story '{current}' is completed. Stopping.")
            sys.exit(0)

        self._hook.block(
            f"STOP BLOCKED: Story '{current}' is not completed. "
            "Finish the current story before stopping."
        )
