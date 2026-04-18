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
       :func:`_apply_report_allow` and resolve again.
    6. Special-case: once ``plan-review`` is completed, ``Hook.discontinue`` so
       the user can read the plan before the workflow auto-advances.

Retry cap (3-strike rule): ``AgentReportGuard`` rejections increment a counter
keyed by ``agent_id``. While ``attempts < max_attempts`` (configured via
``config.specs_max_report_retries``) the dispatcher blocks via ``exit 2`` so
the subagent re-attempts its report. On the cap-th rejection the agent is
marked failed and released — preventing an infinite reject/retry loop.

``last_assistant_message`` is only available on ``SubagentStop`` (not on the
other agent events), which is why score / verdict extraction lives here.

Env override: ``SUBAGENT_STOP_STATE_PATH`` redirects state.jsonl (used by tests).
"""

import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from constants.phases import REVIEW_PHASES
from guardrails import STOP_GUARDS
from guardrails.agent_report_guard import AgentReportGuard
from lib.hook import Hook
from lib.state_store import StateStore
from lib.violations import log_violation
from utils.recorder import Recorder
from utils.resolver import resolve
from config import Config

STATE_PATH = Path(os.environ.get(
    "SUBAGENT_STOP_STATE_PATH",
    str(SCRIPTS_DIR / "state.jsonl"),
))


def _record_agent_completion(state: StateStore, config: Config, agent_id: str) -> None:
    """Mark the agent done and resolve.

    No-op when ``agent_id`` is missing — without an id we can't match the
    in-progress row to update. Resolver ``ValueError`` is converted to
    ``Hook.discontinue`` so terminal-state errors stop the workflow cleanly
    rather than leaking the exception.

    Args:
        state (StateStore): Live workflow state.
        config (Config): Workflow configuration, forwarded to ``resolve``.
        agent_id (str): Tool-use id from the SubagentStop payload.

    Example:
        >>> _record_agent_completion(state, config, "toolu_01abc")  # doctest: +SKIP
    """
    if not agent_id:
        return
    state.update_agent_status(agent_id, "completed")
    try:
        resolve(config, state)
    except ValueError as e:
        Hook.discontinue(str(e))


def _log_report_block(state: StateStore, hook_input: dict, reason: str) -> None:
    """Append a violations.md row for a rejected agent report.

    Args:
        state (StateStore): Source of session_id / workflow_type / story_id /
            prompt_summary / current_phase used as the row's metadata.
        hook_input (dict): Raw SubagentStop payload; ``agent_type`` becomes the
            ``action`` column.
        reason (str): One-line rejection reason (rest of the rejection message
            is intentionally truncated — the full message goes to the model
            via ``Hook.block`` / ``system_message``).

    Example:
        >>> _log_report_block(state, hook_input, "missing scores")  # doctest: +SKIP
    """
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


def _fail_agent_and_release(
    state: StateStore, config: Config, hook_input: dict,
    phase: str, errors: list[str], attempts: int, max_attempts: int,
) -> None:
    """Cap reached — mark the specs agent failed, log once, release the subagent.

    Called only when ``attempts >= max_attempts``. Writes the failure to state,
    appends a single violation row, and emits a ``Hook.system_message`` (which
    exits 0) so the subagent can stop. Without this the agent would loop on
    ``exit 2`` blocks indefinitely.

    Args:
        state (StateStore): Live workflow state; ``mark_specs_agent_failed``
            mutates it.
        config (Config): Workflow configuration (currently unused in the body
            but kept for signature symmetry with the retry-path helper).
        hook_input (dict): Raw SubagentStop payload, used by ``_log_report_block``.
        phase (str): Phase the agent was reporting for.
        errors (list[str]): Validation errors from ``AgentReportGuard``; an
            empty list is replaced with ``["validation failed"]`` so the
            rejection message is never blank.
        attempts (int): Rejection count for this agent (already incremented).
        max_attempts (int): Cap from ``config.specs_max_report_retries``.

    Example:
        >>> _fail_agent_and_release(state, config, hook_input, "vision", ["bad"], 3, 3)  # doctest: +SKIP
    """
    Recorder(state).mark_specs_agent_failed(phase)
    agent_name = AgentReportGuard.SPECS_AGENT_BY_PHASE.get(phase)
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
    """Below cap — block the subagent stop (``exit 2``) so it retries.

    The subagent sees the rejection message on stderr and, per Claude Code
    conventions, will produce a corrected report on the next attempt.

    Args:
        errors (list[str]): Validation errors from ``AgentReportGuard``;
            empty becomes ``["validation failed"]``.
        phase (str): Phase being reported on.
        attempts (int): Rejection count so far (already incremented).
        max_attempts (int): Cap from ``config.specs_max_report_retries``.

    Example:
        >>> _block_for_course_correction(["missing verdict"], "code-review", 1, 3)  # doctest: +SKIP
    """
    Hook.block(
        AgentReportGuard.format_rejection_message(
            phase, errors or ["validation failed"], attempts, max_attempts
        )
    )


def _validate_agent_report(state: StateStore, config: Config, hook_input: dict) -> None:
    """Run ``AgentReportGuard`` for review phases and dispatch the outcome.

    No-op outside of ``REVIEW_PHASES`` — the guard only knows how to validate
    review reports. Dispatches to :func:`_handle_report_block` or
    :func:`_apply_report_allow` based on the guard's decision.

    Args:
        state (StateStore): Live workflow state.
        config (Config): Workflow configuration.
        hook_input (dict): Raw SubagentStop payload.

    Example:
        >>> _validate_agent_report(state, config, hook_input)  # doctest: +SKIP
    """
    if state.current_phase not in REVIEW_PHASES:
        return
    guard = AgentReportGuard(hook_input, config, state)
    decision, _ = guard.validate()
    if decision == "block":
        _handle_report_block(state, config, hook_input, guard)
        return
    _apply_report_allow(state, config, guard)


def _apply_report_allow(state: StateStore, config: Config, guard: AgentReportGuard) -> None:
    """Apply the validated report to state, then resolve.

    Two paths depending on phase:

    - Specs phases (``vision`` / ``architecture`` / ``constitution`` / ``backlog``):
      persist the agent's content as the canonical specs document.
    - Review phases (``plan-review`` / ``code-review`` / ``test-review``): record
      the parsed scores, verdict, and any review-flagged files / tests.

    Mirrors the post-Allow side-effect pattern in ``pre_tool_use.py``: the guard
    stays a pure validator; the dispatcher owns the mutations.

    Args:
        state (StateStore): Live workflow state, mutated by Recorder.
        config (Config): Workflow configuration; passed to ``write_specs_doc``
            and ``resolve``.
        guard (AgentReportGuard): Already-validated guard exposing ``phase``,
            ``content``, ``review_files``, and ``review_tests``.

    Example:
        >>> _apply_report_allow(state, config, guard)  # doctest: +SKIP
    """
    recorder = Recorder(state)
    if guard.phase in AgentReportGuard.SPECS_PHASES:
        recorder.write_specs_doc(guard.phase, guard.content, config)
    else:
        recorder.record_scores(guard.phase, guard.content)
        recorder.record_verdict(guard.phase, guard.content)
        recorder.record_revision_files(guard.phase, guard.review_files, guard.review_tests)
    try:
        resolve(config, state)
    except ValueError as e:
        Hook.discontinue(str(e))


def _handle_report_block(
    state: StateStore, config: Config, hook_input: dict, guard: AgentReportGuard
) -> None:
    """Route a blocked report to either the retry path or the fail-and-release path.

    Bumps the per-agent rejection counter first so both helpers see the same
    incremented value. ``agent_id`` defaults to ``"unknown"`` when missing,
    which still uniquely groups retries within a single dispatcher call.

    Args:
        state (StateStore): Live workflow state; ``bump_agent_rejection_count``
            mutates it.
        config (Config): Source of ``specs_max_report_retries`` (the 3-strike cap).
        hook_input (dict): Raw SubagentStop payload (read for ``agent_id``).
        guard (AgentReportGuard): Failed guard providing ``errors`` and ``phase``.

    Example:
        >>> _handle_report_block(state, config, hook_input, guard)  # doctest: +SKIP
    """
    agent_id = hook_input.get("agent_id", "") or "unknown"
    attempts = state.bump_agent_rejection_count(agent_id)
    max_attempts = config.specs_max_report_retries
    if attempts < max_attempts:
        _block_for_course_correction(guard.errors, guard.phase, attempts, max_attempts)
    _fail_agent_and_release(
        state, config, hook_input, guard.phase, guard.errors, attempts, max_attempts
    )


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
    _record_agent_completion(state, config, hook_input.get("agent_id", ""))
    _validate_agent_report(state, config, hook_input)

    if state.current_phase == "plan-review" and state.is_phase_completed("plan-review"):
        Hook.discontinue("Plan approved. Review the plan before proceeding.")

    sys.exit(0)


if __name__ == "__main__":
    main()
