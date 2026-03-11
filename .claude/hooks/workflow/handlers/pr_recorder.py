"""PostToolUse handler — records PR creation when gh pr create is detected."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.state_store import StateStore
from workflow.workflow_gate import check_workflow_gate
from workflow.config import get as cfg
from workflow.models.hook_input import PostToolUseInput


class PrRecorder:
    def __init__(self, hook_input: PostToolUseInput):
        self._hook_input = hook_input
        self._is_workflow_active = check_workflow_gate()

    def run(self) -> None:
        if not self._is_workflow_active:
            return

        if self._hook_input.tool_name != "Bash":
            return

        command = self._hook_input.tool_input.command
        if "gh pr create" in command:
            state = StateStore(state_path=cfg("paths.workflow_state"))
            state.set("pr_created", True)


if __name__ == "__main__":
    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())
    PrRecorder(hook_input).run()
