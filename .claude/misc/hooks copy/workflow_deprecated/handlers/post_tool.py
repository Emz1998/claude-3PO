#!/usr/bin/env python3
"""PostToolUse handler that routes to appropriate trackers.

Consolidated entry point for all PostToolUse tracking.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore
from trackers.phase_tracker import PhaseTracker  # type: ignore
from trackers.deliverables_tracker import DeliverableTracker  # type: ignore
from trackers.release_plan_tracker import ReleasePlanTracker  # type: ignore
from context.context_injector import ContextInjector  # type: ignore


class PostToolHandler:
    """Handler for PostToolUse events."""

    def __init__(self):
        """Initialize the handler."""
        self._state = get_manager()
        self._phase_tracker = PhaseTracker()
        self._deliverable_tracker = DeliverableTracker()
        self._release_plan_tracker = ReleasePlanTracker()
        self._context_injector = ContextInjector()

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
        if hook_event_name != "PostToolUse":
            return

        tool_name = hook_input.get("tool_name", "")

        # Route to appropriate tracker based on tool
        if tool_name == "Skill":
            # Track phase change
            self._phase_tracker.run(hook_input)
            # Inject context reminder
            self._context_injector.run(hook_input)
            # Track skill deliverable completion
            self._deliverable_tracker.run(hook_input)
            # Record release plan state changes
            self._release_plan_tracker.run_post_tool(hook_input)

        elif tool_name in ["Write", "Edit", "Read", "Bash"]:
            # Track deliverable completion
            self._deliverable_tracker.run(hook_input)


def handle_post_tool(hook_input: dict) -> None:
    """Handle a PostToolUse event.

    Args:
        hook_input: The hook input dictionary
    """
    handler = PostToolHandler()
    handler.run(hook_input)


def main() -> None:
    """Main entry point for the handler."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    handler = PostToolHandler()
    handler.run(hook_input)


if __name__ == "__main__":
    main()
