"""Report guard — blocks stop if report was not written.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads session state and checks validation.report_written == true.
"""

import sys
from pathlib import Path
import json
import subprocess
import re
import yaml
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.lib.file_manager import FileManager
from workflow.constants.config import CODE_EXTENSIONS, TEST_EXTENSIONS


FRONTMATTER_EXTRACTION_PATTERN = r"^\s*---\s*\n([\s\S]*?)\n\s*---"

_SESSIONS_DIR = Path(__file__).resolve().parents[3] / "sessions"
REPORT_FILE_PATH = str(
    _SESSIONS_DIR / "session_{session_id}" / "review" / "{file_name}.md"
)

MAX_REVIEW_DEPTH = 3


def resolve_file_name(written_file_path: str) -> str | None:
    if "plans" in written_file_path:
        return "plan-review"
    if written_file_path.endswith(TEST_EXTENSIONS):
        return "test-review"
    if written_file_path.endswith(CODE_EXTENSIONS):
        return "code-review"
    return None


def resolve_report_file_path(session_id: str, written_file_path: str) -> str | None:
    file_name = resolve_file_name(written_file_path)
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
    file_path: str, session_id: str, written_file_path: str
) -> tuple[bool, str]:
    report_file_path = resolve_report_file_path(session_id, written_file_path)
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


def validate_report(frontmatter: dict | None) -> tuple[bool, str]:

    if frontmatter is None:
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

    return True, "Report is valid."


def build_review_prompt(written_file_path: str) -> str:
    return (
        f"Please review the file at `{written_file_path}` and write a review report.\n"
        "The report must be a Markdown file starting with YAML frontmatter containing:\n"
        "  - confidence_score (integer 0-100)\n"
        "  - quality_score (integer 0-100)\n"
        "  - files_to_revise (list of file paths that need revision)\n"
    )


def run_reviewer(prompt: str, session_id: str | None = None) -> dict:
    command = ["claude", prompt, "--output-format", "json", "--tools", "Read,Grep,Glob"]
    if session_id:
        command.extend(["--resume", session_id])
    result = subprocess.run(command, capture_output=True, text=True)
    return json.loads(result.stdout)


def review(
    prompt: str,
    session_id: str | None = None,
    _depth: int = 0,
) -> str:
    if _depth >= MAX_REVIEW_DEPTH:
        raise RuntimeError(
            "Maximum review retry depth reached. Report could not be validated."
        )

    response = run_reviewer(prompt, session_id)
    claude_session_id = response.get("session_id")
    report_text = response.get("result", "")

    frontmatter = extract_frontmatter(report_text)

    if frontmatter is None:
        return review(
            "The report is not valid. Please add frontmatter with confidence_score and quality_score.",
            claude_session_id,
            _depth + 1,
        )

    valid_report, message = validate_report(frontmatter)
    if not valid_report:
        return review(message, claude_session_id, _depth + 1)

    return report_text


def main() -> None:
    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id")
    if not session_id:
        raise ValueError("Session ID is required")
    session = SessionState(session_id)
    if not session.workflow_active:
        return

    written_file_path = raw_input.get("tool_input", {}).get("file_path")
    prompt = build_review_prompt(written_file_path)
    reviewed_report = review(prompt=prompt, session_id=session_id)

    report_file_path = resolve_report_file_path(session_id, written_file_path)
    if report_file_path is None:
        raise ValueError("Report file path is not found")

    file_manager = FileManager(Path(report_file_path))
    file_manager.save(reviewed_report)


if __name__ == "__main__":
    main()
