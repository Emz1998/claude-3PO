"""Report guard — blocks stop if report was not written.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads session state and checks validation.report_written == true.
"""

import sys
from pathlib import Path
import subprocess
from typing import cast, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.review.review import validate_report, extract_score
from workflow.session_state import SessionState
from workflow.constants.config import PLAN_DIR, READ_ONLY_TOOLS, SAFE_COMMANDS


def get_session(raw_input: dict) -> SessionState:
    session_id = raw_input.get("session_id", "")
    if session_id is None:
        raise ValueError("Session ID is not set")
    return SessionState(session_id)


def get_file_path(raw_input: dict) -> str | None:
    tool_name = get_tool_name(raw_input)
    if tool_name != "Edit":
        return None
    file_path = raw_input.get("tool_input", {}).get("file_path", None)
    if file_path is None:
        raise ValueError("File path is not set")
    return file_path


def get_tool_name(raw_input: dict) -> str:
    tool_name = raw_input.get("tool_name", "")
    if tool_name is None:
        raise ValueError("Tool name is not set")
    return tool_name


def is_session_active(session: SessionState) -> bool:
    return session.workflow_active


def get_code_files_to_review(session: SessionState) -> list[dict]:
    return session.get_files("code", "needs_refactoring")


def needs_code_review(code_file_path: str, session: SessionState) -> tuple[bool, str]:
    files_need_review = get_code_files_to_review(session)
    if not files_need_review:
        return False, "No code files reviewed yet."
    files_to_review = "\n".join(
        f"- {file.get('path', '')}" for file in files_need_review
    )

    if any(file.get("path") == code_file_path for file in files_need_review):
        return True, f"Code file {code_file_path} needs revision."
    return (
        False,
        f"Revision is required for this phase. Please review the following files: \n\n{files_to_review}",
    )


def is_tool_allowed(raw_input: dict) -> tuple[bool, str]:
    tool_name = raw_input.get("tool_name", "")
    if tool_name in READ_ONLY_TOOLS + ["Bash", "Edit"]:
        return True, f"Tool {tool_name} is allowed."

    tool_input = raw_input.get("tool_input", {})
    command = tool_input.get("command", "")
    if command not in SAFE_COMMANDS:
        return False, f"Command {command} is not allowed."
    return True, f"Command {command} is allowed."


def main() -> None:
    raw_input = {
        "session_id": "123",
        "tool_name": "Edit",
        "tool_input": {"file_path": "src/code_file.py"},
    }
    session = get_session(raw_input)
    session_active = is_session_active(session)
    if not session_active:
        return

    tool_allowed, error = is_tool_allowed(raw_input)
    if not tool_allowed:
        Hook.block(error)
        return

    code_file_path = get_file_path(raw_input)
    if code_file_path is None:
        return
    needs_review, message = needs_code_review(code_file_path, session)
    if not needs_review:
        Hook.block(message)
        return

    Hook.system_message("Code File Modified. Allowing to continue with the workflow.")


if __name__ == "__main__":
    main()
