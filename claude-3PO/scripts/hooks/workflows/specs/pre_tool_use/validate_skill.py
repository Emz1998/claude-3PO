"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from typing import Literal
from utils.hook import Hook  # type: ignore
from config import Config  # type: ignore
from pathlib import Path  # type: ignore
from lib.state_store import StateStore  # type: ignore
from utils.order_validation import validate_order  # type: ignore
from lib.resolver import Resolver  # type: ignore
from typing import Any

DEFAULT_STATE_PATH = Path.cwd() / "claude-3PO" / "state.json"


def get_previous_phase(state: StateStore) -> str:
    phases = state.completed_phases
    if not phases:
        return ""
    return phases[-1]["name"]


def is_last_phase_completed(state: StateStore) -> bool:
    return state.current_phases[-1]["status"] == "completed"


def is_skill_allowed(skill: str, config: Config, state: StateStore) -> tuple[bool, str]:
    if not state.all_phases_completed():
        return False, "All phases must be completed before entering a new one"
    if not is_last_phase_completed(state):
        return False, "Last phase must be completed before entering a new one"
    phases = config.get_phase_names_by_workflow(state.workflow_type)
    prev_phase = get_previous_phase(state)
    valid, error = validate_order(prev_phase, skill, phases)
    if not valid:
        return False, error
    return True, f"Skill {skill} is allowed"


def record_skill_invocation(current_skill: str, state: StateStore) -> None:
    state.add_skill(name=current_skill, status="in_progress")
    resolver = Resolver(state)
    resolver.resolve()


def main() -> None:
    hook_input = Hook.read_stdin()
    state = StateStore()
    config = Config()

    next_skill = hook_input.get("tool_input", {}).get("skill", "")

    if next_skill == "review":
        if state.tests_status == "fail":
            Hook.block("Tests must pass before reviewing the code")
            return

    is_allowed, message = is_skill_allowed(next_skill, config, state)
    if not is_allowed:
        Hook.block(message)
        return

    record_skill_invocation(next_skill, state)


if __name__ == "__main__":
    main()
