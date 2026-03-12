"""PostToolUse handler — records story completion status."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import PostToolUseInput
from workflow.constants.phases import STATUS_COMPLETED


class RecordCompletion:
    def __init__(self, hook_input: PostToolUseInput):
        self._hook_input = hook_input
        self._is_workflow_active = check_workflow_gate()

    def parse_args(self) -> tuple[str, str]:
        parts = self._hook_input.tool_input.args.strip().split(" ")
        if len(parts) != 2:
            raise ValueError("Args shouldnt be more than 1")
        return parts[0], parts[1]

    def run(self) -> None:
        if not self._is_workflow_active:
            return

        skill_name = self._hook_input.tool_input.skill
        if skill_name != "log":
            return

        _id, status = self.parse_args()

        if status not in ["Backlog", "Ready", "In progress", "In review", "Done"]:
            Hook.block(f"Invalid status: {status}")

        session = SessionState()
        story_id = session.story_id
        if story_id:
            try:
                def update_status(s: dict) -> None:
                    if status == "Done":
                        s["control"]["status"] = STATUS_COMPLETED

                session.update_session(story_id, update_status)
            except KeyError:
                pass


if __name__ == "__main__":
    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())
    RecordCompletion(hook_input).run()
