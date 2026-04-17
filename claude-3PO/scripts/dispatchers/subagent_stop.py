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
from guardrails.agent_report_guard import AgentReportGuard
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


_SPECS_AGENT_BY_PHASE = {"architect": "Architect", "backlog": "ProductOwner"}


def _fail_agent_and_release(
    state: StateStore, config: Config, hook_input: dict,
    phase: str, errors: list[str], attempts: int, max_attempts: int,
) -> None:
    """Cap reached: mark the specs agent failed, log once, let the subagent stop."""
    agent_name = _SPECS_AGENT_BY_PHASE.get(phase)
    if agent_name:
        state.mark_last_agent_failed(agent_name)
    message = AgentReportGuard.format_rejection_message(
        phase, errors or ["validation failed"], attempts, max_attempts
    )
    _log_report_block(state, hook_input, message.splitlines()[0])
    Hook.system_message(
        f"{agent_name or 'agent'} marked failed after {attempts} rejected attempts. "
        f"Use /continue or re-invoke to proceed.\n\n{message}"
    )


def _block_for_course_correction(
    errors: list[str], phase: str, attempts: int, max_attempts: int
) -> None:
    """Below cap: block the subagent from stopping so it can retry (exit 2)."""
    Hook.block(
        AgentReportGuard.format_rejection_message(
            phase, errors or ["validation failed"], attempts, max_attempts
        )
    )


def _validate_agent_report(state: StateStore, config: Config, hook_input: dict) -> None:
    if state.current_phase not in REVIEW_PHASES:
        return
    guard = AgentReportGuard(hook_input, config, state)
    decision, _ = guard.validate()
    if decision != "block":
        return
    agent_id = hook_input.get("agent_id", "") or "unknown"
    attempts = state.bump_agent_rejection_count(agent_id)
    max_attempts = config.specs_max_report_retries
    if attempts < max_attempts:
        _block_for_course_correction(guard.errors, guard.phase, attempts, max_attempts)
    _fail_agent_and_release(
        state, config, hook_input, guard.phase, guard.errors, attempts, max_attempts
    )


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
