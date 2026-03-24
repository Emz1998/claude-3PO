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
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.review.review import validate_need_iteration, extract_score
from workflow.headless_claude.claude import run_claude
from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.constants.config import MAX_ITERATIONS, PLAN_DIR


def resolve_iteration_left(session: SessionState) -> None:
    iteration_left = cast(int, session.get_file("plan", "iteration_left"))
    if iteration_left is None:
        raise ValueError("Iteration left is not set")
    iteration_left -= 1
    session.set_file("plan", iteration_left=iteration_left)


def is_file_path_valid(plan_path: str) -> bool:
    return Path(plan_path).exists() and Path(plan_path).parent == PLAN_DIR


def get_session(raw_input: dict) -> SessionState:
    session_id = raw_input.get("session_id", "")
    if session_id is None:
        raise ValueError("Session ID is not set")
    return SessionState(session_id)


def get_file_path(raw_input: dict) -> str | None:
    hook_event_name = raw_input.get("hook_event_name", "")
    if hook_event_name not in ["PostToolUse", "PreToolUse"]:
        return None
    tool_name = raw_input.get("tool_name", "")
    if tool_name not in ["Write", "Edit"]:
        return None
    file_path = raw_input.get("plan_path", "")
    if file_path is None:
        raise ValueError("Plan path is not set")
    return file_path


def main() -> None:
    raw_input = Hook.read_stdin()
    session = get_session(raw_input)
    plan_path = get_file_path(raw_input)
    if plan_path is None:
        return

    file_path_valid = is_file_path_valid(plan_path)
    if not file_path_valid:
        return

    plan = cast(str, run_claude("/plan"))
    confidence_score = extract_score("confidence", plan)
    quality_score = extract_score("quality", plan)

    need_iteration = validate_need_iteration(confidence_score, quality_score)

    if need_iteration:
        session.set_file("plan", status="needs_revision")
        return

    Hook.success_response("Plan is valid.")
