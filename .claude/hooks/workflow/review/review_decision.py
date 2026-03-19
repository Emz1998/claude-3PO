"""Review loop — blocks stop if confidence and quality scores are below the thresholds.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads session state and checks validation.decision_invoked == true.
"""

import sys
from pathlib import Path
import re
import yaml
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore
from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.workflow_gate import check_workflow_gate
from workflow.config import get as cfg
from workflow.constants.constants import REVIEWER_AGENTS
from workflow.tool_enforcement.resolve_tool import resolve_tool


CONFIDENCE_THRESHOLD = cfg("validation.confidence_score", 70)
QUALITY_THRESHOLD = cfg("validation.quality_score", 70)
FRONTMATTER_EXTRACTION_PATTERN = r"^---\s*\n([\s\S]*?)\n---"

MAX_ITERATIONS = cfg("validation.iteration_loop", 3)

TMP_STATE_PATH = Path(__file__).resolve().parent / "tmp_state.json"


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


def check_need_iteration(
    confidence_score: int,
    quality_score: int,
    iteration_left: int,
) -> tuple[Literal["escalate", "fail", "pass"], str]:

    if iteration_left <= 0:
        return (
            "escalate",
            "Maximum number of iterations reached. Escalated to user for review.",
        )

    if confidence_score < CONFIDENCE_THRESHOLD or quality_score < QUALITY_THRESHOLD:
        return (
            "fail",
            "Confidence and quality scores are below the thresholds. Please refactor.",
        )

    return (
        "pass",
        "Confidence and quality scores are above the thresholds. Review Loop Passed",
    )


def get_review_type(agent_type: str) -> str:
    match agent_type:
        case "code-reviewer":
            return "code"
        case "plan-reviewer":
            return "plan"
        case "test-reviewer":
            return "test"
        case _:
            raise ValueError(f"Unknown agent type: {agent_type}")


def enforce_file_revision(file_paths: list[str], session: SessionState) -> None:
    for file_path in file_paths:
        session.enforce_tool(tool_name="Write", tool_value=file_path)


def enforce_revision(agent_type: str, session: SessionState) -> None:
    review_state = session.get("review", {})

    result, message = check_need_iteration(
        confidence_score=review_state.get("confidence_score", 0),
        quality_score=review_state.get("quality_score", 0),
        iteration_left=review_state.get("iteration_left", 0),
    )

    if result == "escalate":
        review_type = get_review_type(agent_type)
        escalate_to_user(review_type, session)
        return

    if result == "pass":
        session.set_tool_enforcement_status("active")
        session.cleanup_review()
        return

    iteration_left = review_state.get("iteration_left", 0)
    iteration_left -= 1

    enforce_file_revision(file_paths, session)


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
    enforce_revision(agent_type, session)


if __name__ == "__main__":
    file_paths = ["src/main.py", "src/utils.py"]
    session = SessionState("123")
    enforce_file_revision(file_paths, session)
