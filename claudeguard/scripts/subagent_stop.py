#!/usr/bin/env python3
"""SubagentStop hook — validates agent reports and runs resolvers.

last_assistant_message is only available in SubagentStop.
Used to extract scores (plan/code review) or verdicts (test review).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from guardrails import STOP_GUARDS
from utils.hook import Hook
from utils.state_store import StateStore
from utils.recorder import record_agent_completion
from utils.resolvers import resolve
from config import Config


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(Path(__file__).resolve().parent / "state.jsonl", session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    config = Config()
    agent_id = hook_input.get("agent_id", "")

    # Record agent completion by agent_id
    if agent_id:
        record_agent_completion(agent_id, state)
        try:
            resolve(config, state)
        except ValueError as e:
            Hook.discontinue(str(e))

    # Review phases: validate the agent report (scores/verdict)
    phase = state.current_phase
    if phase in ("plan-review", "test-review", "tests-review", "code-review", "quality-check", "validate"):
        guard = STOP_GUARDS.get("agent_report")
        if guard:
            decision, message = guard(hook_input, config, state)
            if decision == "block":
                Hook.block(message)

    # Checkpoint: plan-review pass → stop for user review
    if phase == "plan-review" and state.is_phase_completed("plan-review"):
        Hook.discontinue("Plan approved. Review the plan before proceeding.")

    sys.exit(0)


if __name__ == "__main__":
    main()
