"""Report ensurer guard — blocks stop if report was not written.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads session state and checks validation.report_written == true.
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.workflow_log import log
from workflow.workflow_gate import check_workflow_gate
from workflow.review.report_guard import resolve_file_name, REPORT_FILE_PATH


def main() -> None:
    is_workflow_active = check_workflow_gate()
    if not is_workflow_active:
        return

    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")
    agent_name = raw_input.get("agent_type", "")
    if not agent_name:
        raise ValueError("Agent name is missing")
    file_name = resolve_file_name(agent_name)
    if file_name is None:
        return

    session = SessionState(session_id)
    report_written = session.get("review", {}).get("report_written", False)

    if not report_written:
        report_file_path = REPORT_FILE_PATH.format(
            session_id=session_id, file_name=file_name
        )
        msg = f"You must write a review report with confidence and quality scores before proceeding to the next phase. Write the report in {report_file_path}"
        Hook.block(msg)
