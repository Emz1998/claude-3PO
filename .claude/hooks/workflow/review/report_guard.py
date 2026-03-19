"""Report guard — blocks stop if report was not written.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads session state and checks validation.report_written == true.
"""

import sys
from pathlib import Path
import re
import yaml
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState, StateStore
from workflow.hook import Hook
from workflow.workflow_log import log
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import PreToolUseInput
from workflow.config import get as cfg


FRONTMATTER_EXTRACTION_PATTERN = r"^\s*---\s*\n([\s\S]*?)\n\s*---"


REPORT_FILE_PATH = (
    "/home/emhar/avaris-ai/.claude/sessions/session_{session_id}/review/{file_name}.md"
)

TMP_STATE_PATH = Path(__file__).resolve().parent / "tmp_state.json"


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
    content = content.strip()
    match = re.match(FRONTMATTER_EXTRACTION_PATTERN, content)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def validate_report_file_path(
    file_path: str, session_id: str, agent_name: str
) -> tuple[bool, str]:
    report_file_path = resolve_report_file_path(session_id, agent_name)
    if file_path != report_file_path:
        return (
            False,
            f"The file path is not the expected file path. Please write or edit the report in the expected file path: {report_file_path}",
        )
    return True, f"File path is valid: {report_file_path}"


def validate_files_to_revise(files_to_revise: Any) -> tuple[bool, str]:

    if not isinstance(files_to_revise, list):
        return (
            False,
            "Files to revise must be a list. Please add files_to_revise to the frontmatter.",
        )

    if not files_to_revise:
        return (
            False,
            "Files to revise are missing. Please add files_to_revise to the frontmatter.",
        )

    non_existent_files = [f for f in files_to_revise if not Path(f).exists()]
    if non_existent_files:
        return (
            False,
            f"Some files to revise do not exist: '{', '.join(non_existent_files)}'. Please add valid file paths to the files_to_revise list.",
        )

    return True, "Files to revise are valid."


def validate_score(score_name: str, score: str | int | None) -> tuple[bool, str]:

    if score is None:
        return (
            False,
            f"{score_name} score is missing. Please add {score_name} to the frontmatter.",
        )

    if not isinstance(score, int):
        return (
            False,
            f"{score_name} score must be an integer. Please change {score_name} to an integer in the frontmatter.",
        )

    if score not in range(0, 101):
        return (
            False,
            f"{score_name} score must be between 0 and 100.",
        )

    return True, f"{score_name} score is valid."


def validate_report(content: str, session: SessionState) -> tuple[bool, str]:
    frontmatter = extract_frontmatter(content)

    if not frontmatter:
        return (
            False,
            "Frontmatter is not present in the review report. Please add frontmatter with confidence_score and quality_score.",
        )

    confidence_score = frontmatter.get("confidence_score")
    quality_score = frontmatter.get("quality_score")
    files_to_revise = frontmatter.get("files_to_revise")

    validations = [
        validate_files_to_revise(files_to_revise),
        validate_score("confidence_score", confidence_score),
        validate_score("quality_score", quality_score),
    ]

    errors = [message for valid, message in validations if not valid]
    if errors:
        return False, "\n".join(errors)

    session.set_review({"files_to_revise": files_to_revise})

    return True, "Report is valid."


def main() -> None:
    is_workflow_active = check_workflow_gate()
    if not is_workflow_active:
        return

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
    agent_name = session.get("agent", {}).get("current", "")
    valid_path, message = validate_report_file_path(file_path, session_id, agent_name)
    if not valid_path:
        Hook.block(message)
        return

    content = tool_input.get("content", "")
    valid_report, message = validate_report(content, session)
    if not valid_report:
        Hook.block(message)
        return


if __name__ == "__main__":
    main()
