"""Report guard — blocks stop if report was not written.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads session state and checks validation.report_written == true.
"""

import sys
from pathlib import Path
import re
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.workflow_log import log
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import PreToolUseInput
from workflow.config import get as cfg

CONFIDENCE_THRESHOLD = cfg("validation.confidence_score", 70)
QUALITY_THRESHOLD = cfg("validation.quality_score", 70)
FRONTMATTER_EXTRACTION_PATTERN = r"^---\s*\n([\s\S]*?)\n---"

MAX_ITERATIONS = cfg("validation.iteration_loop", 3)

REPORT_FILE_PATH = (
    "/home/emhar/avaris-ai/.claude/sessions/session_{session_id}/review/{file_name}.md"
)


def resolve_file_name(agent_name: str) -> str | None:
    match agent_name:
        case "code-reviewer":
            return "code-review"
        case "plan-reviewer":
            return "plan-review"
        case "test-reviewer":
            return "test-review"
        case _:
            return None


def resolve_report_file_path(session_id: str, agent_name: str) -> str | None:
    file_name = resolve_file_name(agent_name)
    if file_name is None:
        return None
    return REPORT_FILE_PATH.format(session_id=session_id, file_name=file_name)


def extract_frontmatter(content: str) -> dict | None:
    match = re.match(FRONTMATTER_EXTRACTION_PATTERN, content)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def main() -> None:
    is_workflow_active = check_workflow_gate()
    if not is_workflow_active:
        return

    log("report_guard", "active", "Report guard started")

    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id")
    if not session_id:
        raise ValueError("Session ID is required")
    tool_name = raw_input.get("tool_name")
    session = SessionState(session_id)

    if tool_name not in ["Write", "Edit"]:
        return

    tool_input = raw_input.get("tool_input", {})
    file_path = tool_input.get("file_path", REPORT_FILE_PATH)
    report_file_name = resolve_file_name(session.get("agent", {}).get("current", ""))
    report_file_path = REPORT_FILE_PATH.format(
        session_id=session_id, file_name=report_file_name
    )

    if file_path != report_file_path:
        Hook.block(
            f"The file path is not the expected file path. Please write or edit the report in the expected file path: {report_file_path}"
        )
        return

    content = tool_input.get("content", "")

    frontmatter = extract_frontmatter(content)

    if not frontmatter:
        return

    confidence_score = frontmatter.get("confidence_score", None)
    quality_score = frontmatter.get("quality_score", None)

    if confidence_score is None or quality_score is None:
        Hook.block(
            "Frontmatter is not present in the review report. Please add a frontmatter with confidence_score and quality_score"
        )
        return

    if confidence_score not in range(0, 101) or quality_score not in range(0, 101):
        Hook.block(
            "Confidence and quality scores must be between 0 and 100. Please add a frontmatter with confidence_score and quality_score"
        )
        return

    session.set_review(
        {
            "report_written": True,
            "confidence_score": confidence_score,
            "quality_score": quality_score,
        },
    )


if __name__ == "__main__":
    main()
