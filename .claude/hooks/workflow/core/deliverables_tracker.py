#!/usr/bin/env python3
"""Deliverables tracker for workflow orchestration.

Manages deliverable initialization, completion tracking, and validation.
"""

import re
import sys
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.unified_loader import get_phase_deliverables_typed  # type: ignore
from core.state_manager import get_manager, StateManager  # type: ignore


class DeliverablesTracker:
    """Tracks deliverables for workflow phases."""

    def __init__(self, state_manager: StateManager | None = None):
        """Initialize the deliverables tracker.

        Args:
            state_manager: Optional state manager instance
        """
        self._state = state_manager or get_manager()

    def initialize_for_phase(self, phase: str) -> None:
        """Initialize deliverables for a phase from config.

        Args:
            phase: Phase name to initialize deliverables for
        """
        phase_deliverables = get_phase_deliverables_typed(phase)
        deliverables: list[dict[str, Any]] = []

        for action in ["read", "write", "edit"]:
            items = getattr(phase_deliverables, action, [])
            for item in items:
                entry: dict[str, Any] = {
                    "type": "files",
                    "action": action,
                    "pattern": item.regex_pattern or item.pattern,
                    "match": item.match,
                    "strict_order": item.strict_order,
                    "completed": False,
                }
                deliverables.append(entry)

        for item in phase_deliverables.bash:
            deliverables.append({
                "type": "commands",
                "action": "bash",
                "pattern": item.command,
                "match": item.match,
                "strict_order": item.strict_order,
                "completed": False,
            })

        for item in phase_deliverables.skill:
            deliverables.append({
                "type": "skill",
                "action": "invoke",
                "pattern": item.name or item.pattern,
                "match": item.match,
                "strict_order": item.strict_order,
                "completed": False,
            })

        self._state.set_deliverables(deliverables)

    def get_deliverables(self) -> list[dict[str, Any]]:
        """Get current deliverables.

        Returns:
            List of deliverable dictionaries
        """
        return self._state.get_deliverables()

    def mark_complete(
        self,
        action: Literal["write", "read", "edit", "bash", "invoke"],
        value: str,
    ) -> bool:
        """Mark a deliverable as completed.

        Args:
            action: The action type (write, read, edit, bash)
            value: The value to match against deliverable patterns

        Returns:
            True if a deliverable was matched and marked complete
        """
        return self._state.mark_deliverable_complete(action, value)

    def are_all_met(self) -> tuple[bool, str]:
        """Check if all deliverables are completed.

        Returns:
            Tuple of (all_met, message)
        """
        return self._state.are_all_deliverables_met()

    def reset_status(self) -> None:
        """Reset all deliverables to incomplete."""
        self._state.reset_deliverables_status()

    def get_incomplete(self) -> list[dict[str, Any]]:
        """Get list of incomplete deliverables.

        Returns:
            List of incomplete deliverable dictionaries
        """
        return [d for d in self.get_deliverables() if not d.get("completed", False)]

    def get_complete(self) -> list[dict[str, Any]]:
        """Get list of completed deliverables.

        Returns:
            List of completed deliverable dictionaries
        """
        return [d for d in self.get_deliverables() if d.get("completed", False)]


# Module-level singleton
_tracker: DeliverablesTracker | None = None


def get_tracker() -> DeliverablesTracker:
    """Get the singleton deliverables tracker instance.

    Returns:
        DeliverablesTracker instance
    """
    global _tracker
    if _tracker is None:
        _tracker = DeliverablesTracker()
    return _tracker


# Convenience functions for backward compatibility
def initialize_deliverables(phase: str) -> None:
    """Initialize deliverables for a phase."""
    get_tracker().initialize_for_phase(phase)


def mark_deliverable_complete(
    action: Literal["write", "read", "edit", "bash", "invoke"],
    value: str,
) -> bool:
    """Mark a deliverable as completed."""
    return get_tracker().mark_complete(action, value)


def are_all_deliverables_met() -> tuple[bool, str]:
    """Check if all deliverables are completed."""
    return get_tracker().are_all_met()


def reset_deliverables_status() -> None:
    """Reset all deliverables to incomplete."""
    get_tracker().reset_status()


def get_deliverable_state() -> list[dict[str, Any]]:
    """Get current deliverables state."""
    return get_tracker().get_deliverables()


if __name__ == "__main__":
    tracker = DeliverablesTracker()
    tracker.initialize_for_phase("explore")
    print(f"Deliverables: {tracker.get_deliverables()}")
    print(f"All met: {tracker.are_all_met()}")
