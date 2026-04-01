"""review_guard.py — SubagentStop handler for all agent types.

Marks agents completed, parses review scores, auto-advances phases.
Uses flat state model.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"

PLAN_REVIEW_THRESHOLD = {"confidence": 80, "quality": 80}
PLAN_REVIEW_MAX = 3


def parse_scores(text: str) -> dict[str, int | None]:
    """Extract confidence and quality scores from free-form reviewer text."""
    confidence = None
    quality = None

    def _last_score(label: str) -> int | None:
        patterns = [
            rf"{label}\s*(?:score|rating)?\s*(?:\*\*)?\s*[:=\-]?\s*(?:\*\*)?\s*(\d+)(?:\s*/\s*100)?",
            rf"{label}\s*(?:score|rating)?\s+(?:is\s+)?(?:\*\*)?\s*(\d+)(?:\s*/\s*100)?",
        ]
        matches: list[str] = []
        for pattern in patterns:
            matches.extend(re.findall(pattern, text, re.IGNORECASE))
        if not matches:
            return None
        return int(matches[-1])

    confidence = _last_score("confidence")
    quality = _last_score("quality")
    return {"confidence": confidence, "quality": quality}


def _required_explore_agents(state: dict) -> dict[str, int]:
    """Return the required agent types/counts for explore phase."""
    required = {}
    if not state.get("skip_explore"):
        required["Explore"] = 3
    if not state.get("skip_research"):
        required["Research"] = 2
    return required


def _count_completed(agents: list[dict], agent_type: str) -> int:
    return sum(1 for a in agents if a.get("agent_type") == agent_type and a.get("status") == "completed")


def _mark_first_running_completed(agents: list[dict], agent_type: str) -> None:
    for a in agents:
        if a.get("agent_type") == agent_type and a.get("status") == "running":
            a["status"] = "completed"
            break


def handle(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Handle SubagentStop: mark agent completed, auto-advance phases.

    Always returns ("allow", "") — never blocks a subagent from stopping.
    """
    agent_type: str = hook_input.get("agent_type", "")
    last_message: str = hook_input.get("last_assistant_message", "")

    def _process(state: dict) -> None:
        if not state.get("workflow_active"):
            return

        phase = state.get("phase", "")
        agents = state.get("agents", [])

        # Mark first matching running agent as completed
        _mark_first_running_completed(agents, agent_type)

        # -----------------------------------------------------------------------
        # Explore / Research: check if all required agents done → advance to plan
        # -----------------------------------------------------------------------
        if agent_type in ("Explore", "Research") and phase == "explore":
            required = _required_explore_agents(state)
            all_done = all(
                _count_completed(agents, atype) >= cnt
                for atype, cnt in required.items()
            )
            if all_done:
                state["phase"] = "plan"

        # -----------------------------------------------------------------------
        # Plan: advance to write-plan
        # -----------------------------------------------------------------------
        elif agent_type == "Plan" and phase == "plan":
            state["phase"] = "write-plan"

        # -----------------------------------------------------------------------
        # PlanReview: parse scores, advance or iterate
        # -----------------------------------------------------------------------
        elif agent_type == "PlanReview" and phase == "review":
            scores = parse_scores(last_message)
            state["plan_review_scores"] = scores
            iteration = state.get("plan_review_iteration", 0)

            passed = (
                scores["confidence"] is not None
                and scores["quality"] is not None
                and scores["confidence"] >= PLAN_REVIEW_THRESHOLD["confidence"]
                and scores["quality"] >= PLAN_REVIEW_THRESHOLD["quality"]
            )

            if passed:
                state["plan_review_status"] = "approved"
                state["phase"] = "approved"
            elif iteration + 1 >= PLAN_REVIEW_MAX:
                state["plan_review_status"] = "max_iterations_reached"
                state["plan_review_iteration"] = iteration + 1
                state["phase"] = "failed"
            else:
                state["plan_review_status"] = "revision_needed"
                state["plan_review_iteration"] = iteration + 1

        # -----------------------------------------------------------------------
        # TaskManager: advance to write-tests or write-code
        # -----------------------------------------------------------------------
        elif agent_type == "TaskManager" and phase == "task-create":
            if state.get("tdd"):
                state["phase"] = "write-tests"
            else:
                state["phase"] = "write-code"

        # -----------------------------------------------------------------------
        # TestReviewer: Parse Pass/Fail → advance or stay
        # -----------------------------------------------------------------------
        elif agent_type == "TestReviewer" and phase == "write-tests":
            verdict = last_message.strip()
            if verdict == "Pass":
                state["test_review_result"] = "Pass"
                state["phase"] = "write-code"
            else:
                state["test_review_result"] = "Fail"
                # Stay in write-tests

        # -----------------------------------------------------------------------
        # Validator: Parse Pass/Fail → advance or return to write-code
        # -----------------------------------------------------------------------
        elif agent_type == "Validator" and phase == "validate":
            verdict = last_message.strip()
            if verdict == "Pass":
                state["validation_result"] = "Pass"
                state["phase"] = "pr-create"
            else:
                state["validation_result"] = "Fail"
                state["phase"] = "write-code"

    store.update(_process)
    return "allow", ""
