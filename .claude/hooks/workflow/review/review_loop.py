"""Decision guard — blocks stop if /decision was not invoked.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads session state and checks validation.decision_invoked == true.
"""

import sys
from pathlib import Path
import re
import yaml
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.workflow_log import log
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import PreToolUseInput
from workflow.config import get as cfg
from workflow.constants.constants import REVIEWER_AGENTS


CONFIDENCE_THRESHOLD = cfg("validation.confidence_score", 70)
QUALITY_THRESHOLD = cfg("validation.quality_score", 70)
FRONTMATTER_EXTRACTION_PATTERN = r"^---\s*\n([\s\S]*?)\n---"

MAX_ITERATIONS = cfg("validation.iteration_loop", 3)


def extract_frontmatter(content: str) -> dict | None:
    match = re.match(FRONTMATTER_EXTRACTION_PATTERN, content)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def escalate_to_user(review_type: str, session: SessionState) -> None:
    session.set(
        "force_stop",
        {
            "reason": f"Maximum number of iterations reached. Escalated to user for {review_type} review.",
            "status": "active",
        },
    )


def check_need_iteration(review_state: dict, session: SessionState) -> tuple[bool, str]:

    confidence_score = review_state.get("confidence_score", 0)
    quality_score = review_state.get("quality_score", 0)
    iteration_left = review_state.get("iteration_left", 0)
    review_type = review_state.get("type", "code")

    if iteration_left <= 0:
        escalate_to_user(review_type, session)
        print("Escalated to user")
        sys.exit(0)

    if confidence_score < CONFIDENCE_THRESHOLD or quality_score < QUALITY_THRESHOLD:
        print(
            "Confidence and quality scores are below the thresholds. Please refactor."
        )
        return (
            True,
            "Confidence and quality scores are below the thresholds. Please refactor.",
        )
    print("Confidence and quality scores are above the thresholds. Review Loop Passed")

    return (
        False,
        "Confidence and quality scores are above the thresholds. Review Loop Passed",
    )


def ensure_next_phase(agent_type: str, session: SessionState) -> None:
    match agent_type:
        case "code-reviewer":
            session.set("phase", {"current": None, "previous": "create-pr"})
            session.add(
                list_type="full_block",
                tool_name="agent",
                tool_value="code-reviewer",
                reason="Please trigger code-reviewer agent",
            )
        case "plan-reviewer":
            session.set("phase", {"current": None, "previous": "plan"})
            session.add(
                list_type="full_block",
                tool_name="exitplanmode",
                tool_value=None,
                reason="Please exit plan mode",
            )
        case "test-reviewer":
            session.add(
                list_type="full_block",
                tool_name="skill",
                tool_value="write-code",
                reason="Please write code",
            )


def ensure_iteration(agent_type: str, session: SessionState) -> None:
    review_state = session.get("review", {})

    need_iteration, message = check_need_iteration(review_state, session)

    if not need_iteration:
        ensure_next_phase(agent_type, session)
        session.cleanup_review()
        return

    iteration_left = review_state.get("iteration_left", 0)
    iteration_left -= 1

    session.set_review(
        {
            "phase": "plan-revision" if agent_type == "plan-reviewer" else "refactor",
            "iteration_left": iteration_left,
        },
    )

    session.add(
        list_type="full_block",
        tool_name="skill",
        tool_value="plan-revision" if agent_type == "plan-reviewer" else "refactor",
        reason=message,
    )


def main() -> None:
    is_workflow_active = check_workflow_gate()
    if not is_workflow_active:
        print("Workflow is not active")
        return

    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")
    agent_type = raw_input.get("tool_input", {}).get("subagent_type", "")

    if agent_type not in REVIEWER_AGENTS:
        print(f"Agent type is not in reviewer agents: {agent_type}")
        return

    session = SessionState(session_id)
    ensure_iteration(agent_type, session)


if __name__ == "__main__":
    agent_type = "code-reviewer"
    session = SessionState("123")
    ensure_iteration(agent_type, session)
