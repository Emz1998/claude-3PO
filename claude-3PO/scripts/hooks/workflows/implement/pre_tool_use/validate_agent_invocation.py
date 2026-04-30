"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from typing import Literal
from utils.hook import Hook  # type: ignore
from config import Config  # type: ignore
from pathlib import Path  # type: ignore
from lib.state_store import StateStore  # type: ignore
from typing import Any, cast, Callable  # type: ignore
from lib.resolver import Resolver  # type: ignore

DEFAULT_STATE_PATH = Path.cwd() / "claude-3PO" / "state.json"


def is_agent_allowed(agent_name: str, state: StateStore) -> tuple[bool, str]:
    config = Config()
    current_phase = state.active_phases

    agents = []

    for phase in current_phase:
        agents.extend(config.get_agent_names_by_phase(phase["name"]))

    if agent_name not in agents:
        return (
            False,
            f"Agent {agent_name} is not allowed when phase {current_phase} is active",
        )
    return (
        True,
        f"Agent {agent_name} is allowed when phase {current_phase} is active",
    )


def record_agent_invocation(agent_name: str, state: StateStore) -> None:
    state.add_agent(name=agent_name, status="in_progress")
    resolver = Resolver(state)
    resolver.resolve()


def main() -> None:
    hook_input = Hook.read_stdin()
    state = StateStore()

    agent_name = hook_input.get("tool_input", {}).get("subagent_type", "")

    is_allowed, message = is_agent_allowed(agent_name, state)
    if not is_allowed:
        Hook.block(message)
        return

    record_agent_invocation(agent_name, state)


if __name__ == "__main__":
    main()
