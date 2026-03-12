"""PreToolUse guard — blocks Agent/Skill when session is on hold or aborted."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import PreToolUseInput
from workflow.constants.phases import STATUS_ABORTED


class HoldChecker:
    def __init__(self, hook_input: PreToolUseInput):
        self._hook_input = hook_input

    def run(self) -> None:
        if not check_workflow_gate():
            return

        session_state = SessionState()
        story_id = session_state.story_id
        if not story_id:
            return

        session = session_state.get_session(story_id)
        if not session:
            return

        control = session.get("control", {})

        if control.get("status") == STATUS_ABORTED:
            Hook.block(f"Session '{story_id}' has been aborted.")

        if control.get("hold", False):
            Hook.block(f"Session '{story_id}' is on hold.")


if __name__ == "__main__":
    hook_input = PreToolUseInput.model_validate(Hook.read_stdin())
    HoldChecker(hook_input).run()
