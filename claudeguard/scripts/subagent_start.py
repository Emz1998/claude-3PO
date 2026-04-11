#!/usr/bin/env python3
"""SubagentStart hook — records agent start with agent_id for tracking."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.hook import Hook
from utils.state_store import StateStore
from utils.recorder import record_agent_start


def main() -> None:
    hook_input = Hook.read_stdin()

    state = StateStore(Path(__file__).resolve().parent / "state.json")
    if not state.get("workflow_active"):
        sys.exit(0)
    if hook_input.get("session_id") != state.get("session_id"):
        sys.exit(0)

    agent_type = hook_input.get("agent_type", "")
    agent_id = hook_input.get("agent_id", "")

    if agent_type and agent_id:
        record_agent_start(agent_type, agent_id, state)

    sys.exit(0)


if __name__ == "__main__":
    main()
