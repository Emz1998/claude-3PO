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
from config.unified_loader import normalize_skill_name, is_bypass_phase  # type: ignore


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
        # Check if troubleshoot is active and we're returning to previous phase
        if self._state.is_troubleshoot_active() and not is_bypass_phase(next_phase):
            pre_phase = self._state.get_pre_troubleshoot_phase()
            if pre_phase == next_phase:
                return True, ""

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
        skill = normalize_skill_name(skill)

        from core.workflow_auditor import get_auditor  # type: ignore

        auditor = get_auditor()

        is_valid, error_message = self.validate(current_phase, skill)
        if not is_valid:
            auditor.log_decision(
                "PHASE_GUARD", "BLOCK", f"{current_phase} -> {skill}: {error_message}"
            )
            print(error_message, file=sys.stderr)
            sys.exit(2)

        auditor.log_decision("PHASE_GUARD", "ALLOW", f"{current_phase} -> {skill}")
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
