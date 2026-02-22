#!/usr/bin/env python3
"""Stop guard: blocks stoppage when the current story is not completed."""

import sys

from scripts.claude_hooks.utils.hook_manager import Hook  # type: ignore
from scripts.claude_hooks.sprint.sprint import Sprint  # type: ignore


class StopGuard(Hook):

    def __init__(self):
        super().__init__()
        self.load_test_data("Stop")
        if self.input.hook_event_name != "Stop":
            print("Not a stop event. Exiting.")
            sys.exit(0)

    def run(self, test: bool | None = True) -> None:
        if test is True:
            self.load_test_data("Stop")
        print("Running stop guard...")
        sprint = Sprint.create()
        current = sprint.state.current_story
        if not current:
            print("No current story. Stopping.")
            sys.exit(0)

        if current in sprint.state.stories.completed:
            print(f"Story '{current}' is completed. Stopping.")
            sys.exit(0)

        self.block(
            f"STOP BLOCKED: Story '{current}' is not completed. "
            "Finish the current story before stopping."
        )
