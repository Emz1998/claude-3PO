"""PostToolUse handler — injects /simplify system message on new file creation during code phase."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import PreToolUseInput
from workflow.workflow_log import log


class GuardRail:
    def __init__(self, hook_input: PreToolUseInput):
        self._hook_input = hook_input

    def run(self) -> None:
        log("GuardRail", "Running", "Guardrail is running")
        if not check_workflow_gate():
            log("GuardRail", "Skipped", "Workflow is not active")
            return

        session_id = self._hook_input.session_id
        session_state = SessionState()
        session = session_state.get_session_by_id(str(session_id))
        if not session:
            log("GuardRail", "Skipped", "Session is not found")
            return

        simplify_status = session.get("simplify", {}).get("status", "inactive")
        if simplify_status == "pending":
            log("GuardRail", "Blocked", "Guardrail needs to be triggered first")
            Hook.block(
                "New file created. Guardrail needs to be triggered first. Please invoke /simplify first."
            )
            return


if __name__ == "__main__":
    hook_input = PreToolUseInput.model_validate(Hook.read_stdin())
    guardrail = GuardRail(hook_input)
    guardrail.run()
