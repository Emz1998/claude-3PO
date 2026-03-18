import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


from workflow.session_state import SessionState
from workflow.models.hook_input import SubagentStartInput
from workflow.hook import Hook
from workflow.config import get as cfg
from workflow.constants.constants import REVIEWER_AGENTS
from workflow.review.report_guard import resolve_file_name, REPORT_FILE_PATH

SESSION = SessionState(cfg("paths.workflow_state"))
PHASES = cfg("phases.workflow")


def main() -> None:
    is_workflow_active = SESSION.workflow_active
    if not is_workflow_active:
        return
    hook_input = SubagentStartInput.model_validate(Hook.read_stdin())
    agent_name = hook_input.agent_type
    session_id = hook_input.session_id

    if agent_name not in REVIEWER_AGENTS:
        return

    SESSION.set_agent("current", agent_name)
    SESSION.set_review({"phase": "in_review", "status": "active"})

    report_file_name = resolve_file_name(agent_name)
    report_file_path = REPORT_FILE_PATH.format(
        session_id=session_id, file_name=report_file_name
    )

    reminder = f"""Reminder you must write a review report in markdown format with confidence_score and quality_score in the frontmatter before stopping.
    Write the report in {report_file_path}"""

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": reminder,
        },
    }

    Hook.advanced_output(output)


if __name__ == "__main__":
    main()
