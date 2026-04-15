#!/usr/bin/env python3
"""SubagentStart hook — records agent start with agent_id for tracking."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from models.state import Agent
from utils.hook import Hook
from utils.state_store import StateStore
from utils.extractors import extract_agent_name


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(Path(__file__).resolve().parent / "state.jsonl", session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    agent_type = extract_agent_name(hook_input, key="agent_type")
    agent_id = hook_input.get("agent_id", "")

    if agent_type and agent_id:
        state.add_agent(Agent(name=agent_type, status="in_progress", tool_use_id=agent_id))

    sys.exit(0)


if __name__ == "__main__":
    main()
