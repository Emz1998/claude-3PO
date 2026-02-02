#!/usr/bin/env python3
"""PreToolUse guard for phase transition validation.

Validates that phase transitions follow the defined order based on test strategy.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore
from core.phase_engine import get_engine, validate_order, get_phase_order  # type: ignore


class PhaseTransitionGuard:
    """Guard for validating phase transitions."""

    def __init__(self, test_strategy: str = "tdd"):
        """Initialize the guard.

        Args:
            test_strategy: Testing strategy for phase ordering
        """
        self._state = get_manager()
        self._engine = get_engine(test_strategy)  # type: ignore

    def is_active(self) -> bool:
        """Check if guard is active (workflow is active)."""
        return self._state.is_workflow_active()

    def validate(self, current_phase: str | None, next_phase: str) -> tuple[bool, str]:
        """Validate a phase transition.

        Args:
            current_phase: Current phase (None if at start)
            next_phase: Target phase

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self._engine.is_valid_transition(current_phase, next_phase)

    def run(self, hook_input: dict) -> None:
        """Run the guard against hook input.

        Args:
            hook_input: The hook input dictionary
        """
        if not self.is_active():
            sys.exit(0)

        hook_event_name = hook_input.get("hook_event_name", "")
        if hook_event_name != "PreToolUse":
            sys.exit(0)

        tool_name = hook_input.get("tool_name", "")
        if tool_name != "Skill":
            sys.exit(0)

        current_phase = self._state.get_current_phase()
        skill = hook_input.get("tool_input", {}).get("skill", "")

        is_valid, error_message = self.validate(current_phase, skill)
        if not is_valid:
            print(error_message, file=sys.stderr)
            sys.exit(2)

        sys.exit(0)


def validate_phase_transition(
    current_phase: str | None, next_phase: str, test_strategy: str = "tdd"
) -> tuple[bool, str]:
    """Validate a phase transition.

    Args:
        current_phase: Current phase
        next_phase: Target phase
        test_strategy: Testing strategy

    Returns:
        Tuple of (is_valid, error_message)
    """
    phase_order = get_phase_order(test_strategy)  # type: ignore
    return validate_order(current_phase, next_phase, phase_order)


def main() -> None:
    """Main entry point for the guard."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    guard = PhaseTransitionGuard()
    guard.run(hook_input)


if __name__ == "__main__":
    main()
