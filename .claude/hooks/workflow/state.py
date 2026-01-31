#!/usr/bin/env python3
"""PostToolUse hook for workflow state tracking."""

import json
import sys
import re
from pathlib import Path
from typing import Any, Literal, Tuple

sys.path.insert(0, str(Path(__file__).parent))

CONFIG_PATH = Path(__file__).parent / "config.yaml"
STATE_PATH = Path(__file__).parent / "state.json"

from _deliverables import load_config  # type: ignore


def load_state(state_path: Path = STATE_PATH) -> dict:
    if state_path.exists():
        try:
            return json.loads(state_path.read_text())
        except (json.JSONDecodeError, IOError, TypeError):
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))


def set_state(key: str, value: Any, state: dict | None = None) -> None:
    if not state:
        state = load_state()
    state[key] = value
    save_state(state)


def get_state(key: str, state: dict | None = None) -> Any | None:
    if not state:
        state = load_state()
    return state.get(key, None)


def add_deliverable(
    _type: Literal["files", "commands", "artifacts"] = "files",
    action: Literal["write", "read", "edit", "bash"] = "write",
    value: str = "",
    state: dict | None = None,
) -> None:
    """Add a deliverable to state for current phase."""
    if not state:
        state = load_state()
    current_phase = state.get("current_phase", "")
    if not current_phase:
        return
    if "deliverables" not in state:
        state["deliverables"] = []
    state["deliverables"].append(
        {
            "type": _type,
            "action": action,
            "value": value,
            "completed": False,
        }
    )
    save_state(state)


def initialize_deliverables_state(
    config: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
) -> None:
    """Initialize deliverables for current phase from config."""
    if config is None:
        config = load_config()
    if state is None:
        state = load_state()

    deliverables_state = []

    current_phase = state.get("current_phase", "")
    if not current_phase:
        return

    phase_deliverables = config.get("deliverables", {}).get(current_phase, [])
    for d in phase_deliverables:
        deliverables_state.append(
            {
                "type": d["type"],
                "action": d["action"],
                "value": d["value"],
                "completed": False,
            }
        )
    state["deliverables"] = deliverables_state
    save_state(state)


def reset_deliverables_state() -> None:
    initialize_deliverables_state()


def get_deliverable_state(state: dict | None = None) -> list[dict[str, Any]]:
    if not state:
        state = load_state()
    return state.get("deliverables", [])


def mark_deliverable_complete(
    action: Literal["write", "read", "edit", "bash"],
    value: str,
    state: dict | None = None,
) -> bool:
    """Mark a deliverable as completed if action and value match.

    Args:
        action: The action type to match (write, read, edit, bash)
        value: The value to match against deliverable values (regex pattern)
        state: Optional state dict, loads from file if not provided

    Returns:
        True if a match was found and marked complete, False otherwise
    """
    print(f"Marking deliverable complete: action={action}, value={value}")
    if not state:
        state = load_state()

    for deliverable in get_deliverable_state(state):
        if deliverable["action"] == action and re.match(deliverable["value"], value):
            deliverable["completed"] = True
            save_state(state)
            return True
    return False


def are_all_deliverables_met(state: dict | None = None) -> Tuple[bool, str]:
    """Check if all deliverables for the current phase are completed."""
    if not state:
        state = load_state()

    phase_deliverables = get_deliverable_state(state)
    if not phase_deliverables:
        return True, "No deliverables found"

    are_all_completed = all(d.get("completed", True) for d in phase_deliverables)
    not_completed_deliverable_names = [
        d.get("value", "") for d in phase_deliverables if not d.get("completed", False)
    ]

    deliverable_names = [d.get("value", "") for d in phase_deliverables]

    return are_all_completed, (
        "All deliverables are completed: " + ", ".join(deliverable_names)
        if are_all_completed
        else "Some deliverables are not completed: "
        + ", ".join(not_completed_deliverable_names)
    )


def initialize_state() -> None:
    """Initialize state with defaults and deliverables for current phase."""
    state = {
        "workflow_active": False,
        "current_phase": "explore",
        "read_files": {},
        "written_files": [],
        "edited_files": [],
        "troubleshoot": False,
        "phase_history": [],
        "deliverables": [],
    }
    save_state(state)
    initialize_deliverables_state(state=state)


def reset_state() -> None:
    """Reset state to defaults."""
    initialize_state()


if __name__ == "__main__":
    reset_state()
