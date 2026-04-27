#!/usr/bin/env python3
"""SubagentStop hook — record agent completion and run resolvers.

Serves the Claude Code ``SubagentStop`` event. Flow:

    1. Read hook stdin; bail (``exit 0``) if no session_id or no active workflow.
    2. Mark the agent as completed in state and run ``resolve`` so any
       phase-completion logic (e.g. all reviewers done) can fire.

In the trimmed 7-phase MVP there are no review phases, so no agent-report
validation runs here. The ``plan`` checkpoint is enforced by the resolver
alone (it pauses auto-advance because ``plan`` carries ``checkpoint: true``).

Env override: ``SUBAGENT_STOP_STATE_PATH`` redirects state.json (used by tests).
"""

import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.hook import Hook
from lib.state_store import StateStore
from utils.hooks.subagent_stop import record_agent_completion
from config import Config

STATE_PATH = Path(os.environ.get(
    "SUBAGENT_STOP_STATE_PATH",
    str(SCRIPTS_DIR / "state.json"),
))


def main() -> None:
    """Entry point — runs once per SubagentStop event.

    Early-exit cascade: no session_id → no active workflow → record the agent's
    completion and run the resolver.

    Example:
        >>> main()  # doctest: +SKIP — reads JSON from stdin and exits
    """
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(STATE_PATH)
    if not state.get("workflow_active"):
        sys.exit(0)

    config = Config()
    record_agent_completion(state, config, hook_input.get("agent_id", ""))

    sys.exit(0)


if __name__ == "__main__":
    main()
