#!/usr/bin/env python3
"""PostToolUse tracker for phase tracking.

Records the current phase when a Skill tool is invoked and initializes deliverables.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore
from core.deliverables_tracker import get_tracker  # type: ignore


class PhaseTracker:
    """Tracker for recording phase changes."""

    def __init__(self):
        """Initialize the tracker."""
        self._state = get_manager()
        self._deliverables = get_tracker()

    def is_active(self) -> bool:
        """Check if tracker is active (workflow is active)."""
        return self._state.is_workflow_active()

    def track(self, skill_name: str) -> None:
        """Track a phase change.

        Args:
            skill_name: The skill/phase name to track
        """
        self._state.set_current_phase(skill_name)
        self._deliverables.initialize_for_phase(skill_name)

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
        if tool_name != "Skill":
            return

        tool_input = hook_input.get("tool_input", {})
        skill_name = tool_input.get("skill", "")

        if skill_name:
            self.track(skill_name)


def track_phase(skill_name: str) -> None:
    """Track a phase change.

    Args:
        skill_name: The skill/phase name
    """
    tracker = PhaseTracker()
    tracker.track(skill_name)


def main() -> None:
    """Main entry point for the tracker."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    tracker = PhaseTracker()
    tracker.run(hook_input)


if __name__ == "__main__":
    main()
