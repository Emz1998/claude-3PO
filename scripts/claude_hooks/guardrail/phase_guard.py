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

from typing import Any, cast
from pathlib import Path
from datetime import datetime
from scripts.claude_hooks.utils.state_store import StateStore  # type: ignore
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.project.paths import ProjectPaths
from scripts.claude_hooks.utils.hook import PreToolUse, Skill


PHASES = ["explore", "plan", "code", "validate" "push"]

CODING_PHASES = ["log", "commit"]


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


class PhaseGuard:
    """Phase transition guard."""

    def __init__(self, hook_input: dict[str, Any]):
        """Initialize the guard."""
        self._sprint = Sprint.create()
        self._hook = PreToolUse(**hook_input)
        paths = ProjectPaths(self._sprint.current_id, self._hook.session_id or "")
        self._state = StateStore(paths.current_session_path / "state.json")

    def validate_transition(self) -> tuple[bool, str]:
        """Validate transition from current phase to next phase."""
        if not isinstance(self._hook.tool_input, Skill):
            return False, "Invalid tool input"
        next_phase = self._hook.tool_input.skill

        if next_phase is None:
            return False, "No skill provided"

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

    def run(self) -> None:
        """Run the test."""
        if not isinstance(self._hook.tool_input, Skill):
            return

        if self._hook.tool_input is None:
            print("Tool input is None")
            return

        if (
            self._hook.tool_input.skill not in PHASES
            and self._hook.tool_input.skill not in CODING_PHASES
        ):
            print("Invalid skill")
            return

        is_valid, reason = self.validate_transition()

        if not is_valid:
            self._hook.block(reason)

        print("Valid Phase")


if __name__ == "__main__":
    phase = PhaseGuard(
        hook_input={
            "tool_name": "Skill",
            "tool_input": {"skill": "explore"},
            "session_id": "123",
            "transcript_path": "/path/to/transcript.json",
            "cwd": "/path/to/cwd",
            "permission_mode": "default",
            "hook_event_name": "PreToolUse",
            "tool_use_id": "123",
        }
    )
    phase.run()
