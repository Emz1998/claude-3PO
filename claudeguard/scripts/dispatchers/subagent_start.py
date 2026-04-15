#!/usr/bin/env python3
"""SubagentStart hook — records agent start with agent_id for tracking."""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from models.state import Agent
from lib.hook import Hook
from lib.state_store import StateStore
from lib.extractors import extract_agent_name


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(SCRIPTS_DIR / "state.jsonl", session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    agent_type = extract_agent_name(hook_input, key="agent_type")
    agent_id = hook_input.get("agent_id", "")

    if agent_type and agent_id:
        state.add_agent(Agent(name=agent_type, status="in_progress", tool_use_id=agent_id))

    sys.exit(0)


if __name__ == "__main__":
    main()
