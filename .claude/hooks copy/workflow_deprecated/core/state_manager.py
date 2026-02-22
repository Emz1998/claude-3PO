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

        return self._state or {}

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
            "troubleshoot": False,
            "sprint_status": {
                deliverable
            }
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
        deliverable_number: int,
        status: Literal["not_started", "in_progress", "completed"],
    ) -> bool:
        """Mark a deliverable as completed if action and value match.

        Args:
            action: The action type to match
            value: The value to match against deliverable patterns

        Returns:
            True if a match was found and marked complete
        """
        deliverables = self.get_deliverables()
        matched = False

        return matched

    def get_min_incomplete_strict_order(self) -> int | None:
        """Get the lowest strict_order among incomplete deliverables.

        Returns:
            Lowest strict_order value, or None if no strict_order items remain.
        """
        deliverables = self.get_deliverables()
        min_order: int | None = None
        for d in deliverables:
            order = d.get("strict_order")
            if order is None:
                continue
            if d.get("completed", False):
                continue
            if min_order is None or order < min_order:
                min_order = order
        return min_order

    def get_strict_order_block_reason(
        self,
        action: str,
        value: str,
    ) -> str | None:
        """Check if a tool call should be blocked by strict_order enforcement.

        Args:
            action: Tool action (read, write, edit, bash, invoke)
            value: File path, command, or skill name

        Returns:
            Block reason string if blocked, None if allowed.
        """
        from config.unified_loader import regex_to_wildcard  # type: ignore

        min_order = self.get_min_incomplete_strict_order()
        if min_order is None:
            return None

        # Check if action/value matches any deliverable at the current min level
        deliverables = self.get_deliverables()
        for d in deliverables:
            if d.get("strict_order") != min_order:
                continue
            if d.get("completed", False):
                continue
            if d.get("action") != action:
                continue
            pattern = d.get("pattern", d.get("value", ""))
            if pattern and re.match(pattern, value):
                return None

        # Build block message listing what needs to be done first
        pending: list[str] = []
        for d in deliverables:
            if d.get("strict_order") != min_order:
                continue
            if d.get("completed", False):
                continue
            pattern = d.get("pattern", d.get("value", ""))
            display = regex_to_wildcard(pattern) if pattern else d.get("action", "")
            desc = d.get("description", "")
            label = f"{d.get('action', '')} {display}"
            if desc:
                label += f" ({desc})"
            pending.append(label)

        return (
            f"STRICT ORDER: Complete level {min_order} deliverables first:\n"
            + "\n".join(f"  - {p}" for p in pending)
        )

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

    def get_pending_validation(self) -> str | None:
        """Get pending validation type.

        Returns:
            "ac", "sc", "epic_sc", or None
        """
        return self.get("pending_validation", None)

    def set_pending_validation(self, validation_type: str) -> None:
        """Set pending validation type.

        Args:
            validation_type: "ac", "sc", or "epic_sc"
        """
        self.set("pending_validation", validation_type)

    def clear_pending_validation(self) -> None:
        """Clear pending validation flag."""
        self.delete("pending_validation")

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

    def is_troubleshoot_active(self) -> bool:
        """Check if troubleshoot mode is active.

        Returns:
            True if troubleshoot is active
        """
        return self.get("troubleshoot", False) is True

    def activate_troubleshoot(self) -> None:
        """Activate troubleshoot mode and store current phase."""
        current = self.get_current_phase()
        self.set("pre_troubleshoot_phase", current)
        self.set("troubleshoot", True)
        self.set_current_phase("troubleshoot")

    def deactivate_troubleshoot(self) -> None:
        """Deactivate troubleshoot and return to previous phase."""
        previous = self.get("pre_troubleshoot_phase")
        self.set("troubleshoot", False)
        if previous:
            self.set_current_phase(previous)
        self.delete("pre_troubleshoot_phase")

    def get_pre_troubleshoot_phase(self) -> str | None:
        """Get the phase before troubleshoot was activated.

        Returns:
            Previous phase name or None
        """
        return self.get("pre_troubleshoot_phase")

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


def initialize_state() -> None:
    """Initialize state with defaults and deliverables for current phase."""
    manager = get_manager()
    manager.reset()
    initialize_deliverables_state()


def initialize_deliverables_state(
    state: dict[str, Any] | None = None,
    phase: str = "",
) -> None:
    """Initialize deliverables for current phase from config."""
    from config.unified_loader import get_phase_deliverables_typed  # type: ignore

    manager = get_manager()
    if state is None:
        state = manager.load()

    if not phase:
        phase = (state or {}).get("current_phase", "")

    phase_deliverables = get_phase_deliverables_typed(phase)
    deliverables_state: list[dict[str, Any]] = []

    for action in ["read", "write", "edit"]:
        items = getattr(phase_deliverables, action, [])
        for item in items:
            deliverables_state.append(
                {
                    "type": "files",
                    "action": action,
                    "value": item.regex_pattern or item.pattern,
                    "match": item.match,
                    "completed": False,
                }
            )

    for item in phase_deliverables.bash:
        deliverables_state.append(
            {
                "type": "commands",
                "action": "bash",
                "value": item.command,
                "match": item.match,
                "completed": False,
            }
        )

    for item in phase_deliverables.skill:
        deliverables_state.append(
            {
                "type": "skill",
                "action": "invoke",
                "value": item.name or item.pattern,
                "match": item.match,
                "completed": False,
            }
        )

    manager.set("deliverables", deliverables_state)


def reset_deliverables_state() -> None:
    """Reset deliverables state by re-initializing from config."""
    initialize_deliverables_state()


def get_deliverable_state(state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Get current deliverables from state."""
    if not state:
        state = get_manager().load()
    return (state or {}).get("deliverables", [])


def add_deliverable(
    _type: Literal["files", "commands", "artifacts"] = "files",
    action: Literal["write", "read", "edit", "bash"] = "write",
    value: str = "",
    state: dict[str, Any] | None = None,
) -> None:
    """Add a deliverable to state for current phase."""
    manager = get_manager()
    if not state:
        state = manager.load()
    current_phase = (state or {}).get("current_phase", "")
    if not current_phase:
        return
    if "deliverables" not in (state or {}):
        state["deliverables"] = []  # type: ignore
    state["deliverables"].append(  # type: ignore
        {
            "type": _type,
            "action": action,
            "value": value,
            "completed": False,
        }
    )
    manager.save(state)


def mark_deliverable_complete(
    action: Literal["write", "read", "edit", "bash"],
    value: str,
    state: dict[str, Any] | None = None,
) -> bool:
    """Mark a deliverable as completed if action and value match."""
    return get_manager().mark_deliverable_complete(action, value)


def are_all_deliverables_met(
    state: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Check if all deliverables for the current phase are completed."""
    return get_manager().are_all_deliverables_met()


def reset_deliverables_status(state: dict[str, Any] | None = None) -> None:
    """Reset all deliverables to incomplete."""
    get_manager().reset_deliverables_status()


if __name__ == "__main__":
    manager = StateManager()
    manager.reset()
    print(f"Workflow active: {manager.is_workflow_active()}")
    print(f"Current phase: {manager.get_current_phase()}")
