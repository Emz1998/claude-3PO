#!/usr/bin/env python3
"""SubagentStop handler for deliverables enforcement.

Blocks subagent termination if deliverables or success criteria are not met.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore
from guards.deliverables_exit import DeliverablesExitGuard  # type: ignore


class SubagentStopHandler:
    """Handler for SubagentStop events."""

    def __init__(self):
        """Initialize the handler."""
        self._state = get_manager()
        self._exit_guard = DeliverablesExitGuard()

    def is_active(self) -> bool:
        """Check if handler is active (workflow is active)."""
        return self._state.is_workflow_active()

    def run(self, hook_input: dict) -> None:
        """Run the handler against hook input.

        Args:
            hook_input: The hook input dictionary
        """
        if not self.is_active():
            sys.exit(0)

        hook_event_name = hook_input.get("hook_event_name", "")
        if hook_event_name != "SubagentStop":
            sys.exit(0)

        # Delegate to exit guard
        self._exit_guard.run(hook_input)


def handle_subagent_stop(hook_input: dict) -> None:
    """Handle a SubagentStop event.

    Args:
        hook_input: The hook input dictionary
    """
    handler = SubagentStopHandler()
    handler.run(hook_input)


def main() -> None:
    """Main entry point for the handler."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    handler = SubagentStopHandler()
    handler.run(hook_input)


if __name__ == "__main__":
    main()
