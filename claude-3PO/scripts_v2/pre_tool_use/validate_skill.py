"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from typing import Literal
from utils.hook import Hook  # type: ignore
from config import Config  # type: ignore
from pathlib import Path  # type: ignore
from lib.store import StateStore  # type: ignore
from utils.order_validation import validate_order  # type: ignore
from lib.resolver import Resolver  # type: ignore

DEFAULT_STATE_PATH = Path.cwd() / "claude-3PO" / "state.json"


def is_skill_allowed(current_skill: str, skills: list[str]) -> tuple[bool, str]:
    valid, error = validate_order(None, current_skill, skills)
    if not valid:
        return False, error
    return True, f"Skill {current_skill} is allowed"


def record_skill_invocation(current_skill: str, state: StateStore) -> None:
    state.add_skill(name=current_skill, status="in_progress")
    resolver = Resolver(state)
    resolver.resolve()


def main() -> None:
    hook_input = Hook.read_stdin()
    state = StateStore()
    config = Config()
    workflow_type = state.workflow_type

    current_skill = hook_input.get("tool_input", {}).get("skill", "")
    skills = config.get_skill_names_by_workflow(workflow_type)

    is_allowed, message = is_skill_allowed(current_skill, skills)
    if not is_allowed:
        Hook.block(message)
        return

    record_skill_invocation(current_skill, state)


if __name__ == "__main__":
    main()
