#!/usr/bin/env python3
"""PostToolUse context injector for phase-specific reminders.

Injects phase-specific context reminders after Skill tool invocations.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json, add_context  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore
from context.phase_reminders import get_phase_reminder  # type: ignore


class ContextInjector:
    """Injector for phase-specific context reminders."""

    def __init__(self):
        """Initialize the injector."""
        self._state = get_manager()

    def is_active(self) -> bool:
        """Check if injector is active (workflow is active)."""
        return self._state.is_workflow_active()

    def inject(self, phase: str) -> bool:
        """Inject context reminder for a phase.

        Args:
            phase: The phase name

        Returns:
            True if reminder was injected
        """
        reminder = get_phase_reminder(phase)
        if not reminder:
            return False

        add_context(reminder, "PostToolUse")
        return True

    def run(self, hook_input: dict) -> None:
        """Run the injector against hook input.

        Args:
            hook_input: The hook input dictionary
        """
        if not self.is_active():
            sys.exit(0)

        hook_event_name = hook_input.get("hook_event_name", "")
        if hook_event_name != "PostToolUse":
            sys.exit(0)

        tool_name = hook_input.get("tool_name", "")
        if tool_name != "Skill":
            sys.exit(0)

        tool_input = hook_input.get("tool_input", {})
        skill_name = tool_input.get("skill", "")

        if not skill_name:
            sys.exit(0)

        self.inject(skill_name)


def inject_phase_context(phase: str) -> bool:
    """Inject context reminder for a phase.

    Args:
        phase: The phase name

    Returns:
        True if reminder was injected
    """
    injector = ContextInjector()
    return injector.inject(phase)


def main() -> None:
    """Main entry point for the injector."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    injector = ContextInjector()
    injector.run(hook_input)


if __name__ == "__main__":
    main()
