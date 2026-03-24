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
from workflow.constants.config import PLAN_DIR


def get_session(raw_input: dict) -> SessionState:
    session_id = raw_input.get("session_id", "")
    if session_id is None:
        raise ValueError("Session ID is not set")
    return SessionState(session_id)


def is_session_active(session: SessionState) -> bool:
    return session.workflow_active


def get_expected_plan_file_path(session: SessionState) -> str | None:
    plan_file_path = session.get_file("plan", "path")
    return cast(str | None, plan_file_path)


def is_edit_tool(tool_name: str) -> bool:
    return tool_name == "Edit"


def is_expected_plan_file_path(
    plan_file_path: str, session: SessionState
) -> tuple[bool, str]:

    plan_file_dir = get_plan_file_dir(plan_file_path)
    if plan_file_dir != PLAN_DIR:
        return False, f"Plan file must be in the {PLAN_DIR} directory."
    expected_plan_file_path = get_expected_plan_file_path(session)
    if plan_file_path != expected_plan_file_path:
        return (
            False,
            f"Plan file path must match the expected plan file path.{expected_plan_file_path}",
        )
    return True, f"Plan file matched the expected plan file path."


def get_plan_file_dir(plan_file_path: str) -> str:
    return str(Path(plan_file_path).parent)


def is_plan_revision_required(session: SessionState) -> bool:
    return session.get_file("plan", "status") == "needs_revision"


def get_file_path(
    action: Literal["Write", "Edit"], raw_input: dict
) -> tuple[str | None, str]:
    hook_event_name = raw_input.get("hook_event_name", "")
    if hook_event_name not in ["PostToolUse", "PreToolUse"]:
        return (
            None,
            "Invalid hook event name. Only PostToolUse and PreToolUse are allowed.",
        )
    tool_name = raw_input.get("tool_name", "")
    if tool_name != action:
        return None, f"Invalid tool name. Only {action} is allowed."
    file_path = raw_input.get("plan_path", "")
    if file_path is None:
        raise ValueError("Plan path is not set")
    return file_path, f"Plan file path is set to {file_path}."


def main() -> None:
    raw_input = Hook.read_stdin()
    session = get_session(raw_input)
    session_active = is_session_active(session)
    if not session_active:
        return

    plan_revision_required = is_plan_revision_required(session)
    if not plan_revision_required:
        return

    plan_file_path, error = get_file_path("Edit", raw_input)

    if plan_file_path is None:
        Hook.block(error)
        return

    expected_plan, error = is_expected_plan_file_path(plan_file_path, session)
    if not expected_plan:
        Hook.block(error)
        return

    Hook.system_message("Plan File Modified. Allowing to continue with the workflow.")
