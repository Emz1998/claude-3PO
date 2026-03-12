"""Validation loop — checks reviewer scores against config thresholds.

Placement: settings.local.json as SubagentStop hook with reviewer matcher.
Reads config.yaml for thresholds and session state for scores.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json

from workflow.session_state import SessionState
from workflow.state_store import StateStore
from workflow.hook import Hook
from workflow.validation.validation_log import log
from workflow.config import get as cfg, get_reviewers
from workflow.workflow_gate import check_workflow_gate

REVIEWER_AGENTS = set(get_reviewers())


def _get_validation_data(session: SessionState) -> tuple[dict, bool]:
    """Get validation data from session or flat state. Returns (validation_dict, is_session)."""
    story_id = session.story_id
    if story_id:
        session_data = session.get_session(story_id)
        if session_data:
            return session_data.get("validation", {}), True

    # Fallback to flat state
    store = StateStore(Path(cfg("paths.workflow_state")))
    state = store.load()
    return state.get("validation", {}), False


def _update_validation(session: SessionState, fn) -> None:
    """Update validation data in session or flat state."""
    story_id = session.story_id
    if story_id:
        try:
            session.update_session(story_id, lambda s: fn(s.get("validation", {}), s))
            return
        except KeyError:
            pass

    # Fallback to flat state
    store = StateStore(Path(cfg("paths.workflow_state")))
    state = store.load()
    validation = state.get("validation", {})
    fn(validation, state)
    store.save(state)


def main() -> None:
    is_workflow_active = check_workflow_gate()
    if not is_workflow_active:
        return

    hook_input = json.loads(sys.stdin.read())
    agent_type = hook_input.get("agent_type", "")

    if agent_type not in REVIEWER_AGENTS:
        log("validation_loop", "SKIP", f"agent_type='{agent_type}' not a reviewer")
        sys.exit(0)

    session = SessionState()
    validation, _ = _get_validation_data(session)

    confidence_score = validation.get("confidence_score", 0)
    iteration_count = validation.get("iteration_count", 0)
    max_iterations = cfg("validation.iteration_loop")
    threshold = cfg("validation.confidence_score")

    if confidence_score >= threshold:
        log(
            "validation_loop",
            "ALLOW",
            f"agent='{agent_type}' confidence={confidence_score} >= threshold={threshold}, state reset",
        )
        Hook.advanced_output(
            {"continue": False, "stopReason": f"Allowed", "systemMessage": f"Allowed"}
        )
        return

    # Score below threshold
    if iteration_count >= max_iterations:
        # Escalate — allow stop but warn
        msg = f"ESCALATION: Confidence score {confidence_score} still below threshold {threshold} after {max_iterations} iterations. Escalating to user."
        log("validation_loop", "ESCALATE", f"agent='{agent_type}' {msg}")

        def escalate(v: dict, s: dict) -> None:
            v["escalate_to_user"] = True
            v["escalated_by"] = agent_type

        _update_validation(session, escalate)

        Hook.advanced_output(
            {"continue": False, "stopReason": f"Iteration Exhausted by {agent_type}"}
        )
        return

    # Block — iterate
    iteration_count += 1

    def update_for_retry(v: dict, s: dict) -> None:
        v["decision_invoked"] = False
        v["iteration_count"] = iteration_count

    _update_validation(session, update_for_retry)

    msg = f"Confidence score {confidence_score} below threshold {threshold}. Re-review needed (iteration {iteration_count}/{max_iterations})."
    log("validation_loop", "BLOCK", f"agent='{agent_type}' {msg}")
    Hook.block(msg)


if __name__ == "__main__":
    main()
