"""PreToolUse handler — validates workflow phase ordering."""

from typing import Any

from scripts.claude_hooks.constants import PHASES, CODING_PHASES
from scripts.claude_hooks.models import PreToolUse, Skill
from scripts.claude_hooks.responses import block
from scripts.claude_hooks.state_store import StateStore
from scripts.claude_hooks.paths import ProjectPaths
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.handlers.workflow_gate import check_workflow_gate


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


def _validate_transition(hook: PreToolUse, state: StateStore) -> tuple[bool, str]:
    """Validate transition from current phase to next phase."""
    if not isinstance(hook.tool_input, Skill):
        return False, "Invalid tool input"
    next_phase = hook.tool_input.skill

    if next_phase is None:
        return False, "No skill provided"

    recent_phase = state.get("recent_phase", "explore")
    if recent_phase == "code" and next_phase in CODING_PHASES:
        recent_coding_phase = state.get("recent_coding_phase")
        print(f"Recent coding phase: '{recent_coding_phase}'")
        return validate_order(recent_coding_phase, next_phase, CODING_PHASES)

    if recent_phase != "code" and next_phase in CODING_PHASES:
        reason = f"Cannot start coding phase '{next_phase}' from non-code phase '{recent_phase}'"
        reason += f"\nFinish phases {PHASES[0]} and {PHASES[1]} first before starting coding phase '{next_phase}'"
        return False, reason

    return validate_order(recent_phase, next_phase, PHASES)


def handle(hook_input: dict[str, Any]) -> None:
    """Phase guard handler."""
    if not check_workflow_gate():
        return
    hook = PreToolUse(**hook_input)
    if not isinstance(hook.tool_input, Skill):
        return
    if hook.tool_input is None:
        return
    if (
        hook.tool_input.skill not in PHASES
        and hook.tool_input.skill not in CODING_PHASES
    ):
        return

    sprint = Sprint.create()
    paths = ProjectPaths(sprint.current_id, hook.session_id or "")
    state = StateStore(paths.current_session_path / "state.json")

    is_valid, reason = _validate_transition(hook, state)
    if not is_valid:
        block(reason)

    print("Valid Phase")
