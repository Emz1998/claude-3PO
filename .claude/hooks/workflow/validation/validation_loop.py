"""Validation loop — checks reviewer scores against config thresholds.

Placement: settings.local.json as SubagentStop hook with reviewer matcher.
Reads config.yaml for thresholds and state.json for scores.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json

from workflow.state_store import StateStore
from workflow.hook import Hook
from workflow.validation.validation_log import log
from workflow.config import get as cfg

STATE_PATH = Path(cfg("paths.workflow_state"))

REVIEWER_AGENTS = set(cfg("agents.reviewers"))


def main() -> None:
    hook_input = json.loads(sys.stdin.read())
    agent_type = hook_input.get("agent_type", "")

    if agent_type not in REVIEWER_AGENTS:
        log("validation_loop", "SKIP", f"agent_type='{agent_type}' not a reviewer")
        sys.exit(0)

    store = StateStore(STATE_PATH)
    state = store.load()
    validation = state.get("validation", {})

    confidence_score = validation.get("confidence_score", 0)
    iteration_count = validation.get("iteration_count", 0)
    max_iterations = cfg("validation.iteration_loop")
    threshold = cfg("validation.confidence_score")

    if confidence_score >= threshold:
        # Pass — reset validation state
        def reset_validation(s: dict) -> None:
            s["validation"] = {
                "decision_invoked": False,
                "confidence_score": 0,
                "quality_score": 0,
                "iteration_count": 0,
            }

        store.update(reset_validation)
        log("validation_loop", "ALLOW", f"agent='{agent_type}' confidence={confidence_score} >= threshold={threshold}, state reset")
        sys.exit(0)

    # Score below threshold
    if iteration_count >= max_iterations:
        # Escalate — allow stop but warn
        msg = f"ESCALATION: Confidence score {confidence_score} still below threshold {threshold} after {max_iterations} iterations. Escalating to user."
        log("validation_loop", "ESCALATE", f"agent='{agent_type}' {msg}")
        Hook.success_response(msg)

    # Block — iterate
    iteration_count += 1

    def update_for_retry(s: dict) -> None:
        s["validation"]["decision_invoked"] = False
        s["validation"]["iteration_count"] = iteration_count

    store.update(update_for_retry)

    msg = f"Confidence score {confidence_score} below threshold {threshold}. Re-review needed (iteration {iteration_count}/{max_iterations})."
    log("validation_loop", "BLOCK", f"agent='{agent_type}' {msg}")
    Hook.block(msg)


if __name__ == "__main__":
    main()
