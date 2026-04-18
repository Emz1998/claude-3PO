#!/usr/bin/env python3
"""SubagentStart hook — register a launching subagent in workflow state.

Serves the Claude Code ``SubagentStart`` event. Flow:

    1. Read hook stdin; bail (``exit 0``) if no session_id or no active workflow.
    2. Pull ``agent_type`` (the subagent's role, e.g. ``code-reviewer``) and
       ``agent_id`` (the unique tool-use id) from the payload.
    3. If both are present, append an ``Agent`` row with ``status="in_progress"``
       to the workflow state. The ``agent_id`` is what later events (Stop /
       Completed) use to look this row back up.

Always exits 0 — this hook is purely an observer; it never blocks.
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from models.state import Agent
from lib.hook import Hook
from lib.state_store import StateStore
from lib.extractors import extract_agent_name


def main() -> None:
    """Entry point — runs once per SubagentStart event.

    Records the launching subagent in state. Skips silently if either
    ``agent_type`` or ``agent_id`` is missing — without both we can't reliably
    correlate this start with the matching stop event.

    Example:
        >>> main()  # doctest: +SKIP — reads JSON from stdin and exits
    """
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
