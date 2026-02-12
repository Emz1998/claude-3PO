#!/usr/bin/env python3
"""PreToolUse guard for subagent invocation validation.

Validates that the correct subagent is being invoked for the current workflow phase.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore
from core.phase_engine import get_engine, get_phase_subagent  # type: ignore


class SubagentAccessGuard:
    """Guard for validating subagent access by phase."""

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

    def is_subagent_allowed(self, phase: str, subagent: str) -> bool:
        """Check if a subagent is allowed for a phase.

        Args:
            phase: Current phase
            subagent: Subagent being invoked

        Returns:
            True if subagent is allowed
        """
        return self._engine.is_subagent_allowed(phase, subagent)

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
        if tool_name != "Task":
            sys.exit(0)

        current_phase = self._state.get_current_phase()
        subagent = hook_input.get("tool_input", {}).get("subagent_type", "")

        from core.workflow_auditor import get_auditor  # type: ignore

        auditor = get_auditor()

        if not self.is_subagent_allowed(current_phase, subagent):
            allowed = get_phase_subagent(current_phase)
            auditor.log_decision("SUBAGENT_GUARD", "BLOCK", f"'{subagent}' in phase '{current_phase}'")
            print(
                f'Subagent "{subagent}" not allowed in phase "{current_phase}". '
                f'Expected: "{allowed}"',
                file=sys.stderr,
            )
            sys.exit(2)

        auditor.log_decision("SUBAGENT_GUARD", "ALLOW", f"'{subagent}' in phase '{current_phase}'")
        sys.exit(0)


def validate_subagent_access(phase: str, subagent: str) -> tuple[bool, str]:
    """Validate subagent access for a phase.

    Args:
        phase: Current phase
        subagent: Subagent being invoked

    Returns:
        Tuple of (is_allowed, error_message)
    """
    engine = get_engine()  # type: ignore
    if engine.is_subagent_allowed(phase, subagent):
        return True, ""

    allowed = get_phase_subagent(phase)
    return False, f'Subagent "{subagent}" not allowed in phase "{phase}". Expected: "{allowed}"'


def main() -> None:
    """Main entry point for the guard."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    guard = SubagentAccessGuard()
    guard.run(hook_input)


if __name__ == "__main__":
    main()
