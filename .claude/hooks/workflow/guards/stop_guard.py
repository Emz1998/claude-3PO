"""Stop handler — blocks stoppage when the current story is not completed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import StopInput
from workflow.constants.phases import STATUS_COMPLETED


class StopGuard:
    def __init__(self, hook_input: StopInput):
        self._hook_input = hook_input
        self._is_workflow_active = check_workflow_gate()

    def run(self) -> None:
        if not self._is_workflow_active:
            return

        session_state = SessionState()
        story_id = session_state.story_id
        if not story_id:
            return

        session = session_state.get_session(story_id)
        if not session:
            return

        # Check control status
        control_status = session.get("control", {}).get("status")
        if control_status != STATUS_COMPLETED:
            Hook.block(f"Story '{story_id}' is not completed.")

        # Check PR created
        pr_created = session.get("pr", {}).get("created", False)
        if not pr_created:
            Hook.block("PR has not been created yet.")


if __name__ == "__main__":
    hook_input = StopInput.model_validate(Hook.read_stdin())
    StopGuard(hook_input).run()
