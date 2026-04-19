#!/usr/bin/env python3
"""SubagentStop hook — validate the agent's report, then run resolvers.

Serves the Claude Code ``SubagentStop`` event. Flow:

    1. Read hook stdin; bail (``exit 0``) if no session_id or no active workflow.
    2. Mark the agent as completed in state and run ``resolve`` so any
       phase-completion logic (e.g. all reviewers done) can fire.
    3. If the current phase is a review phase, hand the report to
       ``AgentReportGuard`` for validation.
    4. On block: bump the per-agent rejection counter and either retry (block
       via ``exit 2``) or, after the 3-strike cap, mark the agent failed and
       release the subagent (``exit 0`` with a system message).
    5. On allow: write specs docs / record review scores via
       :func:`utils.hooks.subagent_stop.apply_report_allow` and resolve again.
    6. Special-case: once ``plan-review`` is completed, ``Hook.discontinue`` so
       the user can read the plan before the workflow auto-advances.

Retry cap (3-strike rule): ``AgentReportGuard`` rejections increment a counter
keyed by ``agent_id``. While ``attempts < max_attempts`` (configured via
``config.specs_max_report_retries``) the dispatcher blocks via ``exit 2`` so
the subagent re-attempts its report. On the cap-th rejection the agent is
marked failed and released — preventing an infinite reject/retry loop.

``last_assistant_message`` is only available on ``SubagentStop`` (not on the
other agent events), which is why score / verdict extraction lives in the
orchestration module.

Env override: ``SUBAGENT_STOP_STATE_PATH`` redirects state.jsonl (used by tests).
"""

import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.hook import Hook
from lib.state_store import StateStore
from utils.hooks.subagent_stop import record_agent_completion, validate_agent_report
from config import Config

STATE_PATH = Path(os.environ.get(
    "SUBAGENT_STOP_STATE_PATH",
    str(SCRIPTS_DIR / "state.jsonl"),
))


def main() -> None:
    """Entry point — runs once per SubagentStop event.

    Early-exit cascade: no session_id → no active workflow → record the agent's
    completion → validate its report → finally, on a completed ``plan-review``
    phase, ``Hook.discontinue`` so the user can read the plan before anything
    else auto-advances.

    Example:
        >>> main()  # doctest: +SKIP — reads JSON from stdin and exits
    """
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    state = StateStore(STATE_PATH, session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)

    config = Config()
    record_agent_completion(state, config, hook_input.get("agent_id", ""))
    validate_agent_report(state, config, hook_input)

    if state.current_phase == "plan-review" and state.is_phase_completed("plan-review"):
        Hook.discontinue("Plan approved. Review the plan before proceeding.")

    sys.exit(0)


if __name__ == "__main__":
    main()
