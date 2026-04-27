"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from typing import Literal
from utils.hook import Hook  # type: ignore
from config import Config  # type: ignore
from pathlib import Path  # type: ignore
from lib.store import StateStore  # type: ignore
from typing import Any, cast, Callable
from lib.conformance_check import template_conformance_check  # type: ignore
from utils.template_retriever import retrieve_template  # type: ignore

DEFAULT_STATE_PATH = Path.cwd() / "claude-3PO" / "state.json"


def is_agent_response_valid(
    hook_input: dict[str, Any], state: StateStore
) -> tuple[bool, str]:
    agent_name = hook_input.get("agent_type", str)
    response = hook_input.get("last_assistant_message", str)
    template = retrieve_template(agent_name)
    ok, diff = template_conformance_check(template, response)
    if not ok:
        return (
            False,
            f"Agent response is not valid\n\n{diff}",
        )
    return True, "Agent response is valid"


def main() -> None:
    hook_input = Hook.read_stdin()
    state = StateStore()

    is_valid, message = is_agent_response_valid(hook_input, state)
    if not is_valid:
        Hook.block(message)
        return


if __name__ == "__main__":
    main()
