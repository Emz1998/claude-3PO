"""Review guard — handles SubagentStop: records completion, parses review scores, auto-advances phases."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.guards.agent_guard import count_completed
from workflow.guards.phase_guard import PHASE_ORDER
from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"

REVIEWER_TO_REVIEW_KEY = {
    "plan-reviewer": "plan",
    "test-reviewer":  "tests",
}

# Phase completion requirements: agent_type → minimum completed count
PHASE_COMPLETION: dict[str, dict[str, int]] = {
    "explore":  {"codebase-explorer": 3, "research-specialist": 2},
    "decision": {"tech-lead": 1},
    "validate": {"qa-expert": 1},
    "pr-create": {"version-manager": 1},
}

def parse_scores(text: str) -> dict[str, int | None]:
    """Extract confidence and quality scores from free-form reviewer text."""
    confidence = None
    quality = None

    m = re.search(r'confidence\s*(?:score)?[\s:=is]+(\d+)', text, re.IGNORECASE)
    if m:
        confidence = int(m.group(1))

    m = re.search(r'quality\s*(?:score)?[\s:=is]+(\d+)', text, re.IGNORECASE)
    if m:
        quality = int(m.group(1))

    return {"confidence": confidence, "quality": quality}


def advance_next_phase(phases: list[dict], current_name: str) -> None:
    """Mark current phase completed and next pending phase in_progress."""
    for p in phases:
        if p["name"] == current_name:
            p["status"] = "completed"
            break
    current_idx = PHASE_ORDER.index(current_name)
    if current_idx + 1 < len(PHASE_ORDER):
        next_name = PHASE_ORDER[current_idx + 1]
        for p in phases:
            if p["name"] == next_name and p["status"] == "pending":
                p["status"] = "in_progress"
                break


def handle(hook_input: dict, state_path: Path | None = None) -> tuple[str, str]:
    """Handle SubagentStop: mark agent completed, parse review scores, auto-advance phases.

    Always returns ("allow", "") — never blocks a subagent from stopping.
    """
    agent_type: str = hook_input.get("agent_type", "")
    last_message: str = hook_input.get("last_assistant_message", "")

    path = state_path or DEFAULT_STATE_PATH
    store = StateStore(path)

    result: dict = {}

    def _process(state: dict) -> None:
        phases: list[dict] = state.get("phases", [])
        current = next((p for p in phases if p["status"] == "in_progress"), None)
        if current is None:
            return

        phase_name = current["name"]
        agents: list[dict] = current.get("agents", [])

        # Mark first matching "running" agent as completed
        for a in agents:
            if a.get("agent_type") == agent_type and a.get("status") == "running":
                a["status"] = "completed"
                break

        # Handle reviewer agents
        review_key = REVIEWER_TO_REVIEW_KEY.get(agent_type)
        if review_key:
            review = state.get("review", {}).get(review_key, {})
            scores = parse_scores(last_message)
            threshold = review.get("threshold", {"confidence": 80, "quality": 80})
            iteration = review.get("iteration", 0)
            max_iter = review.get("max_iterations", 3)

            # Update scores in state
            if "review" not in state:
                state["review"] = {}
            if review_key not in state["review"]:
                state["review"][review_key] = {}
            state["review"][review_key]["scores"] = scores

            passed = (
                scores["confidence"] is not None
                and scores["quality"] is not None
                and scores["confidence"] >= threshold["confidence"]
                and scores["quality"] >= threshold["quality"]
            )

            if passed:
                state["review"][review_key]["status"] = "approved"
                advance_next_phase(phases, phase_name)
            elif iteration + 1 >= max_iter:
                state["review"][review_key]["status"] = "max_iterations_reached"
                state["review"][review_key]["iteration"] = iteration + 1
                for p in phases:
                    if p["name"] == phase_name:
                        p["status"] = "failed"
                        break
            else:
                state["review"][review_key]["status"] = "revision_needed"
                state["review"][review_key]["iteration"] = iteration + 1
            return

        # Non-reviewer: check if phase completion criteria met
        completion = PHASE_COMPLETION.get(phase_name)
        if completion:
            all_done = all(
                count_completed(agents, atype) >= required
                for atype, required in completion.items()
            )
            if all_done:
                advance_next_phase(phases, phase_name)

    store.update(_process)
    return "allow", ""
