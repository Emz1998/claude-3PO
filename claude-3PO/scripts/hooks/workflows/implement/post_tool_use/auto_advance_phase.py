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

AUTO_ADVANCE_PHASES = {
    "plan": "create-tasks",
    "create-tasks": "write-tests",
    "test-review": "write-code",
}


def get_auto_phase(skill: str) -> str:
    return AUTO_ADVANCE_PHASES.get(skill, "")


def main() -> None:
    hook_input = Hook.read_stdin()

    next_skill = hook_input.get("tool_input", {}).get("skill", "")
    auto_phase = get_auto_phase(next_skill)
    if auto_phase:
        state = StateStore()
        state.add_phase(name=auto_phase, status="not_started")
        return


if __name__ == "__main__":
    main()
