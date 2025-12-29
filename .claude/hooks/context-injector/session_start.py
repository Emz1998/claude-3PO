#!/usr/bin/env python3
"""Inject context into hook output for implement workflow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import add_context, get_status, read_stdin_json, set_status  # type: ignore
from roadmap import (  # type: ignore
    get_current_task_id,
    get_current_milestone_id,
    get_current_phase_id,
    get_current_version,
)

TEMPLATE = """
Session ID: {session_id}
Current Version: {current_version}
Current Phase: {current_phase}
Current Milestone: {current_milestone}
Current Task: {current_task}
"""

STDIN_TEST = {
    "session_id": "1234567890",
}


def get_session_id() -> str:
    """Get session id from hook input."""
    hook_input = STDIN_TEST
    return hook_input.get("session_id", "")


def build_context() -> str:
    """Build context string from project status."""

    status_keys = {
        "session_id": get_session_id(),
        "current_version": get_current_version(),
        "current_phase": get_current_phase_id(),
        "current_milestone": get_current_milestone_id(),
        "current_task": get_current_task_id(),
    }

    return TEMPLATE.format(**status_keys)


def inject_context() -> None:
    """Inject workflow context into session."""
    try:
        hook_input = read_stdin_json()
        session_id = hook_input.get("session_id", "")

        # Store session id in status
        if session_id:
            set_status("current_session_id", session_id)

        context = build_context()
        add_context(context)

    except Exception as e:
        print(f"Context injection error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    inject_context()
