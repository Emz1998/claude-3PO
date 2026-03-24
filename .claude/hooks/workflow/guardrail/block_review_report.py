"""Report guard — blocks stop if report was not written.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads session state and checks validation.report_written == true.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.review.review import validate_report, extract_score
from workflow.session_state import SessionState


def get_session(raw_input: dict) -> SessionState:
    session_id = raw_input.get("session_id", "")
    if session_id is None:
        raise ValueError("Session ID is not set")
    return SessionState(session_id)


def main() -> None:
    raw_input = Hook.read_stdin()
    session = get_session(raw_input)
    if not session.workflow_active:
        return

    hook_event_name = raw_input.get("hook_event_name", "")
    if hook_event_name != "Stop":
        return

    last_assistant_message = raw_input.get("last_assistant_message", "")
    confidence_score = extract_score("confidence", last_assistant_message)
    quality_score = extract_score("quality", last_assistant_message)

    valid_report, message = validate_report(confidence_score, quality_score)
    if not valid_report:
        Hook.block(message)
        return

    Hook.system_message(message)
