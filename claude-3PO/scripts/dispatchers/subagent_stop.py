#!/usr/bin/env python3
"""SubagentStop hook — validates agent reports and runs resolvers.

last_assistant_message is only available in SubagentStop.
Used to extract scores (plan/code review) or verdicts (test review).
"""

import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from guardrails import STOP_GUARDS
from lib.hook import Hook
from lib.state_store import StateStore
from lib.violations import log_violation
from utils.resolver import resolve
from config import Config

STATE_PATH = Path(os.environ.get(
    "SUBAGENT_STOP_STATE_PATH",
    str(SCRIPTS_DIR / "state.jsonl"),
))

REVIEW_PHASES = (
    "plan-review", "test-review", "tests-review",
    "code-review", "quality-check", "validate",
    "architect", "backlog",
)


def _record_agent_completion(state: StateStore, config: Config, agent_id: str) -> None:
    if not agent_id:
        return
    state.update_agent_status(agent_id, "completed")
    try:
        resolve(config, state)
    except ValueError as e:
        Hook.discontinue(str(e))


def _log_report_block(state: StateStore, hook_input: dict, reason: str) -> None:
    agent_type = hook_input.get("agent_type", "") or ""
    log_violation(
        session_id=state.session_id,
        workflow_type=state.get("workflow_type", "build"),
        story_id=state.get("story_id"),
        prompt_summary=state.get("prompt_summary"),
        phase=state.current_phase,
        tool="SubagentStop",
        action=agent_type,
        reason=reason,
    )


def _validate_agent_report(state: StateStore, config: Config, hook_input: dict) -> None:
    if state.current_phase not in REVIEW_PHASES:
        return
    guard = STOP_GUARDS.get("agent_report")
    if not guard:
        return
    decision, message = guard(hook_input, config, state)
    if decision == "block":
        _log_report_block(state, hook_input, message)
        Hook.block(message)


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(STATE_PATH, session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    config = Config()
    _record_agent_completion(state, config, hook_input.get("agent_id", ""))
    _validate_agent_report(state, config, hook_input)

    if state.current_phase == "plan-review" and state.is_phase_completed("plan-review"):
        Hook.discontinue("Plan approved. Review the plan before proceeding.")

    sys.exit(0)


if __name__ == "__main__":
    main()
