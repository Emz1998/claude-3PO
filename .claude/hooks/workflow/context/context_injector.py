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
from config.unified_loader import normalize_skill_name  # type: ignore


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

    def inject_validation_context(self) -> bool:
        """Inject validation context if pending_validation is set.

        Returns:
            True if validation context was injected
        """
        pending = self._state.get_pending_validation()
        if not pending:
            return False

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from validators.criteria_validator import (  # type: ignore
                get_unmet_acs,
                get_unmet_scs,
                get_unmet_epic_scs,
            )

            type_labels = {
                "ac": "Acceptance Criteria (AC)",
                "sc": "Success Criteria (SC)",
                "epic_sc": "Epic Success Criteria (ESC)",
            }
            label = type_labels.get(pending, pending)

            if pending == "ac":
                unmet_ids = get_unmet_acs()
            elif pending == "sc":
                unmet_ids = get_unmet_scs()
            elif pending == "epic_sc":
                unmet_ids = get_unmet_epic_scs()
            else:
                unmet_ids = []

            unmet_str = ", ".join(unmet_ids) if unmet_ids else "unknown"
            context = (
                f"VALIDATION REQUIRED: Deploy the validator subagent to validate "
                f"{label} before proceeding with normal workflow phases. "
                f"Unmet criteria: {unmet_str}"
            )

            add_context(context, "PostToolUse")
            return True
        except ImportError:
            return False

    def run(self, hook_input: dict) -> None:
        """Run the injector against hook input.

        Args:
            hook_input: The hook input dictionary
        """
        if not self.is_active():
            sys.exit(0)

        # Check for pending validation and inject context
        if self.inject_validation_context():
            return

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

        skill_name = normalize_skill_name(skill_name)
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
