#!/usr/bin/env python3
"""Unified state manager for workflow orchestration.

Provides a clean API for workflow state operations, wrapping state.json.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Literal

STATE_PATH = Path(__file__).parent.parent / "state.json"


class StateManager:
    """Unified API for workflow state management."""

    def __init__(self, state_path: Path = STATE_PATH):
        """Initialize the state manager.

        Args:
            state_path: Path to the state.json file
        """
        self._state_path = state_path
        self._state: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        """Load state from file.

        Returns:
            State dictionary
        """
        if self._state_path.exists():
            try:
                self._state = json.loads(self._state_path.read_text())
            except (json.JSONDecodeError, IOError, TypeError):
                self._state = {}
        else:
            self._state = {}
        return self._state

    def save(self, state: dict[str, Any] | None = None) -> None:
        """Save state to file.

        Args:
            state: State dictionary to save (uses internal state if None)
        """
        if state is not None:
            self._state = state
        if self._state is not None:
            self._state_path.write_text(json.dumps(self._state, indent=2))

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from state.

        Args:
            key: State key to retrieve
            default: Default value if key not found

        Returns:
            Value for key or default
        """
        if self._state is None:
            self.load()
        return (self._state or {}).get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in state and save.

        Args:
            key: State key to set
            value: Value to set
        """
        if self._state is None:
            self.load()
        if self._state is None:
            self._state = {}
        self._state[key] = value
        self.save()

    def delete(self, key: str) -> None:
        """Delete a key from state.

        Args:
            key: State key to delete
        """
        if self._state is None:
            self.load()
        if self._state and key in self._state:
            del self._state[key]
            self.save()

    def reset(self) -> None:
        """Reset state to defaults."""
        self._state = {
            "workflow_active": False,
            "current_phase": "explore",
            "read_files": {},
            "written_files": [],
            "edited_files": [],
            "troubleshoot": False,
            "phase_history": [],
            "deliverables": [],
            "dry_run_active": False,
        }
        self.save()

    def is_workflow_active(self) -> bool:
        """Check if workflow is active.

        Returns:
            True if workflow is active
        """
        return self.get("workflow_active", False) is True

    def activate_workflow(self) -> None:
        """Activate the workflow."""
        self.set("workflow_active", True)

    def deactivate_workflow(self) -> None:
        """Deactivate the workflow."""
        self.set("workflow_active", False)

    def get_current_phase(self) -> str:
        """Get the current workflow phase.

        Returns:
            Current phase name
        """
        return self.get("current_phase", "explore")

    def set_current_phase(self, phase: str) -> None:
        """Set the current workflow phase.

        Args:
            phase: Phase name to set
        """
        self.set("current_phase", phase)

    def get_deliverables(self) -> list[dict[str, Any]]:
        """Get current phase deliverables.

        Returns:
            List of deliverable dictionaries
        """
        return self.get("deliverables", [])

    def set_deliverables(self, deliverables: list[dict[str, Any]]) -> None:
        """Set deliverables for current phase.

        Args:
            deliverables: List of deliverable dictionaries
        """
        self.set("deliverables", deliverables)

    def mark_deliverable_complete(
        self,
        action: Literal["write", "read", "edit", "bash", "invoke"],
        value: str,
    ) -> bool:
        """Mark a deliverable as completed if action and value match.

        Only marks complete if all higher-priority deliverables are done.

        Args:
            action: The action type to match
            value: The value to match against deliverable patterns

        Returns:
            True if a match was found and marked complete
        """
        deliverables = self.get_deliverables()
        for deliverable in deliverables:
            if deliverable.get("action") == action:
                pattern = deliverable.get("pattern", deliverable.get("value", ""))
                if re.match(pattern, value):
                    # Check priority enforcement
                    if not self._can_complete_deliverable(deliverable, deliverables):
                        return False
                    deliverable["completed"] = True
                    self.set_deliverables(deliverables)
                    return True
        return False

    def _can_complete_deliverable(
        self, target: dict[str, Any], all_deliverables: list[dict[str, Any]]
    ) -> bool:
        """Check if target deliverable can be completed based on priority.

        Returns True if all higher-priority deliverables are already completed.

        Args:
            target: The deliverable attempting to be completed
            all_deliverables: All deliverables for the current phase

        Returns:
            True if target can be completed (all higher priority items done)
        """
        target_priority = target.get("priority")
        if target_priority is None:
            return True  # No priority = can always complete

        for d in all_deliverables:
            d_priority = d.get("priority")
            if d_priority is None:
                continue  # Skip deliverables without priority
            if d_priority < target_priority and not d.get("completed", False):
                return False  # Higher priority item not completed
        return True

    def are_all_deliverables_met(self) -> tuple[bool, str]:
        """Check if all deliverables are completed.

        Returns:
            Tuple of (all_met, message)
        """
        deliverables = self.get_deliverables()
        if not deliverables:
            return True, "No deliverables found"

        incomplete = [
            d.get("pattern", d.get("value", ""))
            for d in deliverables
            if not d.get("completed", False)
        ]

        if incomplete:
            return False, f"Incomplete deliverables: {', '.join(incomplete)}"

        return True, "All deliverables completed"

    def is_dry_run_active(self) -> bool:
        """Check if dry run mode is active.

        Returns:
            True if dry run is active
        """
        return self.get("dry_run_active", False) is True

    def activate_dry_run(self) -> None:
        """Activate dry run mode."""
        self.set("dry_run_active", True)

    def deactivate_dry_run(self) -> None:
        """Deactivate dry run mode."""
        self.set("dry_run_active", False)

    def reset_deliverables_status(self) -> None:
        """Reset all deliverables to incomplete."""
        deliverables = self.get_deliverables()
        for d in deliverables:
            d["completed"] = False
        self.set_deliverables(deliverables)


# Module-level singleton instance
_manager: StateManager | None = None


def get_manager() -> StateManager:
    """Get the singleton state manager instance.

    Returns:
        StateManager instance
    """
    global _manager
    if _manager is None:
        _manager = StateManager()
    return _manager


# Convenience functions for backward compatibility
def load_state(state_path: Path = STATE_PATH) -> dict[str, Any]:
    """Load state from file."""
    return get_manager().load()


def save_state(state: dict[str, Any]) -> None:
    """Save state to file."""
    get_manager().save(state)


def get_state(key: str, default: Any = None) -> Any:
    """Get a value from state."""
    return get_manager().get(key, default)


def set_state(key: str, value: Any) -> None:
    """Set a value in state."""
    get_manager().set(key, value)


def reset_state() -> None:
    """Reset state to defaults."""
    get_manager().reset()


if __name__ == "__main__":
    manager = StateManager()
    manager.reset()
    print(f"Workflow active: {manager.is_workflow_active()}")
    print(f"Current phase: {manager.get_current_phase()}")
