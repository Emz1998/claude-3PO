"""utils.hooks.subagent_stop — orchestration helpers for the SubagentStop hook.

Extracted from ``dispatchers/subagent_stop.py`` so the dispatcher file holds
only ``main()``. Every function here is callable independently and ordered
roughly in the sequence ``main()`` uses them.
"""

from handlers.guardrails.agent_report_guard import AgentReportGuard
from constants.phases import REVIEW_PHASES
from lib.extractors import extract_scores, extract_verdict
from lib.hook import Hook
from lib.scoring import scores_valid, verdict_valid
from lib.specs_validation import format_rejection_message
from lib.state_store import StateStore
from lib.violations import log_violation
from utils.recorder import Recorder
from utils.resolver import resolve
from config import Config


def record_agent_completion(state: StateStore, config: Config, agent_id: str) -> None:
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
        >>> record_agent_completion(state, config, "toolu_01abc")  # doctest: +SKIP

    SideEffect:
        Flips the agent row's status to ``completed`` and runs the resolver,
        which may advance the current phase.
    """
    # Empty agent_id means the payload can't identify which in-progress row to
    # update — silently bail rather than corrupt an unrelated row.
    if not agent_id:
        return
    state.update_agent_status(agent_id, "completed")
    try:
        resolve(config, state)
    except ValueError as e:
        Hook.discontinue(str(e))


def log_report_block(state: StateStore, hook_input: dict, reason: str) -> None:
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
        >>> log_report_block(state, hook_input, "missing scores")  # doctest: +SKIP

    SideEffect:
        Appends a row to ``violations.md``.
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


def fail_agent_and_release(
    state: StateStore, config: Config, hook_input: dict,
    phase: str, errors: list[str], attempts: int, max_attempts: int,
) -> None:
    """Cap reached — log once and release the subagent so it can stop.

    Called only when ``attempts >= max_attempts``. Appends a single violation
    row and emits a ``Hook.system_message`` (which exits 0) so the subagent
    can stop. Without this the agent would loop on ``exit 2`` blocks
    indefinitely.

    Args:
        state (StateStore): Live workflow state.
        config (Config): Workflow configuration (currently unused in the body
            but kept for signature symmetry with the retry-path helper).
        hook_input (dict): Raw SubagentStop payload, used by
            :func:`log_report_block`.
        phase (str): Phase the agent was reporting for.
        errors (list[str]): Validation errors from ``AgentReportGuard``; an
            empty list is replaced with ``["validation failed"]`` so the
            rejection message is never blank.
        attempts (int): Rejection count for this agent (already incremented).
        max_attempts (int): Cap from ``config.specs_max_report_retries``.

    Example:
        >>> fail_agent_and_release(state, config, hook_input, "vision", ["bad"], 3, 3)  # doctest: +SKIP

    SideEffect:
        Writes a violation row and emits a system message (which exits 0).
    """
    agent_name = AgentReportGuard.SPECS_AGENT_BY_PHASE.get(phase)
    message = format_rejection_message(
        phase, errors or ["validation failed"], attempts, max_attempts
    )
    # Only the first line goes into violations.md; the full message is routed
    # back to the agent via system_message so the retry reason survives.
    log_report_block(state, hook_input, message.splitlines()[0])
    Hook.system_message(
        f"{agent_name or 'agent'} released after {attempts} rejected attempts. "
        f"Use /continue or re-invoke to proceed.\n\n{message}"
    )


def block_for_course_correction(
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
        >>> block_for_course_correction(["missing verdict"], "code-review", 1, 3)  # doctest: +SKIP

    SideEffect:
        Exits the process with code 2 via ``Hook.block``.
    """
    Hook.block(
        format_rejection_message(
            phase, errors or ["validation failed"], attempts, max_attempts
        )
    )


def validate_agent_report(state: StateStore, config: Config, hook_input: dict) -> None:
    """Run ``AgentReportGuard`` for review phases and dispatch the outcome.

    No-op outside of ``REVIEW_PHASES`` — the guard only knows how to validate
    review reports. Dispatches to :func:`handle_report_block` or
    :func:`apply_report_allow` based on the guard's decision.

    Args:
        state (StateStore): Live workflow state.
        config (Config): Workflow configuration.
        hook_input (dict): Raw SubagentStop payload.

    Example:
        >>> validate_agent_report(state, config, hook_input)  # doctest: +SKIP

    SideEffect:
        Via the block/allow branches, mutates state, writes violations, or
        exits the process.
    """
    if state.current_phase not in REVIEW_PHASES:
        return
    guard = AgentReportGuard(hook_input, config, state)
    decision, _ = guard.validate()
    if decision == "block":
        handle_report_block(state, config, hook_input, guard)
        return
    apply_report_allow(state, config, guard)


def apply_report_allow(state: StateStore, config: Config, guard: AgentReportGuard) -> None:
    """Apply the validated review report to state, then resolve.

    Handles only the review phases (``code-review`` / ``test-review``)
    through the narrow 19-method Recorder API. Specs-doc writing and
    plan-review recording are dropped as part of the Recorder refactor.

    Args:
        state (StateStore): Live workflow state, mutated by Recorder.
        config (Config): Workflow configuration; passed to ``resolve``.
        guard (AgentReportGuard): Already-validated guard exposing ``phase``
            and ``content``.

    Example:
        >>> apply_report_allow(state, config, guard)  # doctest: +SKIP

    SideEffect:
        Records review scores/verdict via Recorder and runs the resolver.
    """
    recorder = Recorder(state)
    # Two phase-specific recording paths — scores for code-review, verdict for
    # test-review — so the downstream state mirrors the right extractor.
    if guard.phase == "code-review":
        _, scores = scores_valid(guard.content, extract_scores)
        recorder.record_code_review(state.code_review_count + 1, scores)
    elif guard.phase == "test-review":
        _, verdict = verdict_valid(guard.content, extract_verdict)
        recorder.record_test_review(state.test_review_count + 1, verdict)
    try:
        resolve(config, state)
    except ValueError as e:
        Hook.discontinue(str(e))


def handle_report_block(
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
        >>> handle_report_block(state, config, hook_input, guard)  # doctest: +SKIP

    SideEffect:
        Increments the rejection counter and either exits 2 (retry) or exits 0
        with a system message (cap hit).
    """
    agent_id = hook_input.get("agent_id", "") or "unknown"
    attempts = state.bump_agent_rejection_count(agent_id)
    max_attempts = config.specs_max_report_retries
    # Below the cap → block so the agent retries; at/above the cap → fall
    # through to fail_agent_and_release (which exits 0 via system_message).
    if attempts < max_attempts:
        block_for_course_correction(guard.errors, guard.phase, attempts, max_attempts)
    fail_agent_and_release(
        state, config, hook_input, guard.phase, guard.errors, attempts, max_attempts
    )
