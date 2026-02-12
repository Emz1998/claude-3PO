#!/usr/bin/env python3
"""SubagentStop guard for deliverable enforcement.

Blocks subagent termination if deliverables or success criteria are not met.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore
from core.deliverables_tracker import get_tracker  # type: ignore


class DeliverablesExitGuard:
    """Guard for validating deliverables before exit."""

    def __init__(self):
        """Initialize the guard."""
        self._state = get_manager()
        self._tracker = get_tracker()

    def is_active(self) -> bool:
        """Check if guard is active (workflow is active)."""
        return self._state.is_workflow_active()

    def validate_deliverables(self) -> tuple[bool, str]:
        """Validate that all deliverables are met.

        Returns:
            Tuple of (all_met, message)
        """
        return self._tracker.are_all_met()

    def validate_scs(self) -> tuple[bool, str]:
        """Validate that all success criteria are met.

        Returns:
            Tuple of (all_met, message)
        """
        # Import here to avoid circular imports
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from roadmap.utils import are_all_scs_met_in_milestone  # type: ignore
            return are_all_scs_met_in_milestone()
        except ImportError:
            from core.workflow_auditor import get_auditor  # type: ignore

            get_auditor().log_warn(
                "SC_SKIP",
                "SC validation unavailable (ImportError) — exit allowed without SC check",
            )
            return True, "SC validation not available"

    def run(self, hook_input: dict) -> None:
        """Run the guard against hook input.

        Args:
            hook_input: The hook input dictionary
        """
        if not self.is_active():
            sys.exit(0)

        deliverables_met, del_message = self.validate_deliverables()
        scs_met, scs_message = self.validate_scs()

        from core.workflow_auditor import get_auditor  # type: ignore

        auditor = get_auditor()

        if not deliverables_met or not scs_met:
            reason = del_message if not deliverables_met else scs_message
            auditor.log_decision("EXIT_GUARD", "BLOCK", reason)
            decision = {
                "decision": "block",
                "reason": reason,
            }
            print(json.dumps(decision))
            sys.exit(2)

        total = len(self._tracker.get_deliverables())
        complete = len(self._tracker.get_complete())
        auditor.log_decision("EXIT_GUARD", "ALLOW", f"{complete}/{total} deliverables met")
        sys.exit(0)


def validate_deliverables_exit() -> tuple[bool, str]:
    """Validate that all deliverables and SCs are met.

    Returns:
        Tuple of (all_met, combined_message)
    """
    guard = DeliverablesExitGuard()

    del_met, del_msg = guard.validate_deliverables()
    if not del_met:
        return False, del_msg

    scs_met, scs_msg = guard.validate_scs()
    if not scs_met:
        return False, scs_msg

    return True, "All requirements met"


def main() -> None:
    """Main entry point for the guard."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    guard = DeliverablesExitGuard()
    guard.run(hook_input)


if __name__ == "__main__":
    main()
