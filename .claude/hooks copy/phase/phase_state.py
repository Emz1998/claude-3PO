#!/usr/bin/env python3
"""PreToolUse guardrail for /implement workflow subagent ordering.

Ensures subagents are triggered in the correct order:
1. codebase-explorer (requires TODO_READ state)
2. planning-specialist (requires EXPLORER_DONE state)
3. plan-consultant (requires PLANNER_DONE state)
4. Then coding workflow based on TDD/TA/DEFAULT mode

Blocks subagent execution (exit 2) if triggered out of order.
Uses task owner from roadmap.json to determine expected engineer subagent.
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import StateManager  # type: ignore
from utils import Hook  # type: ignore


PHASES = ["explore", "plan", "code", "push"]

CODING_PHASES = ["mark", "validate", "commit"]

STATE_PATH = Path(".claude/hooks/phase/state.json")


def validate_order(
    current_item: str | None, next_item: str, order: list[str]
) -> tuple[bool, str]:
    """Validate transition based on item order (generic).

    Args:
        current_item: Current item (None if at start)
        next_item: Target item
        order: List of items in valid order

    Returns:
        Tuple of (is_valid, error_message)
    """
    if next_item not in order:
        return False, f"Invalid next item: '{next_item}'"

    if current_item is None:
        if next_item == order[0]:
            return True, ""
        return False, f"Must start with '{order[0]}', not '{next_item}'"

    if current_item not in order:
        return False, f"Invalid current item: '{current_item}'"

    current_idx = order.index(current_item)
    new_idx = order.index(next_item)

    if new_idx < current_idx:
        return False, f"Cannot go backwards from '{current_item}' to '{next_item}'"

    if new_idx > current_idx + 1:
        skipped = order[current_idx + 1 : new_idx]
        return False, f"Must complete {skipped} before '{next_item}'"

    return True, ""


class Phase(Hook):
    """Phase transition guard."""

    def __init__(self, phase: str):
        """Initialize the guard."""
        super().__init__()
        self._state = StateManager(STATE_PATH)

    @property
    def state(self) -> StateManager:
        """Get the state."""
        return self._state

    @state.setter
    def state(self, state: StateManager) -> None:
        """Set the state."""
        self._state = state

    def reset(self) -> None:
        """Reset the state."""
        self._state.reset()
        self._state.initialize(
            {"recent_phase": "explore", "recent_coding_phase": "mark"}
        )

    def record(self) -> None:
        """Record the phase."""
        next_phase = self.input.to_dict().get("tool_input", {}).get("skill", None)
        recent_phase = self._state.get("recent_phase", "explore")
        if next_phase not in PHASES and next_phase not in CODING_PHASES:
            print(f"Invalid phase: '{next_phase}'")
            print(f"Recent phase stays as '{recent_phase}'")
            return
        if next_phase in CODING_PHASES:
            self._state.set("recent_coding_phase", next_phase)
            return
        self._state.set("recent_phase", next_phase)

    def validate(self) -> tuple[bool, str]:
        """Validate transition from current phase to next phase."""
        next_phase = self.input.to_dict().get("tool_input", {}).get("skill", None)
        recent_phase = self._state.get("recent_phase", "explore")
        if recent_phase == "code" and next_phase in CODING_PHASES:
            recent_coding_phase = self._state.get("recent_coding_phase")

            print(f"Recent coding phase: '{recent_coding_phase}'")
            return validate_order(recent_coding_phase, next_phase, CODING_PHASES)

        if recent_phase != "code" and next_phase in CODING_PHASES:
            reason = f"Cannot start coding phase '{next_phase}' from non-code phase '{recent_phase}'"
            reason += f"\nFinish phases {PHASES[0]} and {PHASES[1]} first before starting coding phase '{next_phase}'"
            return (False, reason)
        return validate_order(recent_phase, next_phase, PHASES)

    def run_test(self) -> None:
        """Run the test."""
        self.test("PreToolUse", "Skill")
        is_valid, reason = self.validate()
        if not is_valid:
            self.block(reason)

        self.record()

    def setup_guardrail(self) -> None:
        """Run the phase."""
        is_valid, reason = self.validate()
        if not is_valid:
            self.block(reason)
            return
        self.record()
