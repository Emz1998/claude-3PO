#!/usr/bin/env python3
"""PostToolUse tracker for deliverable completion.

Marks deliverables as complete when Write, Edit, Read, or Bash tools are used.
"""

import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore
from core.deliverables_tracker import get_tracker as get_deliverables_tracker  # type: ignore


class DeliverableTracker:
    """Tracker for marking deliverables complete."""

    def __init__(self):
        """Initialize the tracker."""
        self._state = get_manager()
        self._deliverables = get_deliverables_tracker()

    def is_active(self) -> bool:
        """Check if tracker is active (workflow is active)."""
        return self._state.is_workflow_active()

    def track(
        self,
        action: Literal["write", "read", "edit", "bash", "invoke"],
        value: str,
    ) -> bool:
        """Track a deliverable completion.

        Args:
            action: The action type
            value: The file path, command, or skill name

        Returns:
            True if deliverable was marked complete
        """
        return self._deliverables.mark_complete(action, value)

    def run(self, hook_input: dict) -> None:
        """Run the tracker against hook input.

        Args:
            hook_input: The hook input dictionary
        """
        if not self.is_active():
            sys.exit(0)

        hook_event_name = hook_input.get("hook_event_name", "")
        if hook_event_name != "PostToolUse":
            return

        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})

        if tool_name == "Write":
            file_path = tool_input.get("file_path", "")
            if file_path:
                self.track("write", file_path)
            return

        if tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
            if file_path:
                self.track("edit", file_path)
            return

        if tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            if file_path:
                self.track("read", file_path)
            return

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if command:
                self.track("bash", command)
            return

        if tool_name == "Skill":
            skill_name = tool_input.get("skill", "")
            if skill_name:
                self.track("invoke", skill_name)
            return


def track_deliverable(
    action: Literal["write", "read", "edit", "bash", "invoke"],
    value: str,
) -> bool:
    """Track a deliverable completion.

    Args:
        action: The action type
        value: The file path or command

    Returns:
        True if deliverable was marked complete
    """
    tracker = DeliverableTracker()
    return tracker.track(action, value)


def main() -> None:
    """Main entry point for the tracker."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    tracker = DeliverableTracker()
    tracker.run(hook_input)


if __name__ == "__main__":
    main()
