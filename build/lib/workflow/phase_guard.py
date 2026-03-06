"""PreToolUse handler — validates workflow phase ordering."""

from typing import Any
from pathlib import Path

from workflow.constants.phases import PHASES, CODING_PHASES
from workflow.state_store import StateStore
from workflow.hook import Hook, PreToolUse
from workflow.workflow_gate import check_workflow_gate


def validate_order(
    current_item: str | None, next_item: str, order: list[str]
) -> tuple[bool, str]:
    """Validate transition based on item order."""
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


def _validate_transition(
    hook: Hook[PreToolUse], state_store: StateStore
) -> tuple[bool, str]:
    """Validate transition from current phase to next phase."""

    next_phase = hook.input.tool_input.skill

    if next_phase is None:
        return False, "No skill provided"

    state = state_store.load() or {}
    recent_phase = state.get("recent_phase", "explore")
    if recent_phase == "code" and next_phase in CODING_PHASES:
        recent_coding_phase = state.get("recent_coding_phase")
        return validate_order(recent_coding_phase, next_phase, CODING_PHASES)

    if recent_phase != "code" and next_phase in CODING_PHASES:
        reason = f"Cannot start coding phase '{next_phase}' from non-code phase '{recent_phase}'"
        reason += f"\nFinish phases {PHASES[0]} and {PHASES[1]} first before starting coding phase '{next_phase}'"
        return False, reason

    return validate_order(recent_phase, next_phase, PHASES)


class PhaseGuard(PreToolUse):
    def __init__(self):
        self.state_store = StateStore(Path("project/state.json"))
        self._hook = Hook[PreToolUse]().create()
        self._is_workflow_active = check_workflow_gate()

    def validate_transition(self) -> tuple[bool, str]:
        return _validate_transition(self._hook, self.state_store)

    @property
    def is_skill_in_phases(self) -> bool:
        return (
            self._hook.input.tool_input.skill in PHASES
            or self._hook.input.tool_input.skill in CODING_PHASES
        )

    def run(self) -> None:
        if not self._is_workflow_active:
            return
        if not self.is_skill_in_phases:
            return
        is_valid, reason = self.validate_transition()
        if not is_valid:
            self._hook.block(reason)


if __name__ == "__main__":
    phase_guard = PhaseGuard()
    phase_guard.run()
