import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.workflow_log import log
from workflow.workflow_gate import check_workflow_gate
from workflow.utils.review_dir import get_review_dir
from workflow.state_handlers.release_full_block import release_full_block


CODE_REVIEW_MESSAGE = "Need code review. Please invoke agent-code-reviewer to review the refactoring changes."


def main() -> None:
    is_workflow_active = check_workflow_gate()

    if not is_workflow_active:
        return
    raw_input = Hook.read_stdin()
    session_id = raw_input.get("session_id", "")
    hook_event_name = raw_input.get("hook_event_name")
    if hook_event_name != "Stop":
        return

    log(hook_name="refactor", status="active", message="Stop hook triggered")
    session = SessionState(session_id)
    release_full_block(input_tool_name="skill", input_tool_value="refactor")
    session.add(
        list_type="full_block",
        tool_name="agent",
        tool_value="code-reviewer",
        reason=CODE_REVIEW_MESSAGE,
    )


if __name__ == "__main__":
    main()
