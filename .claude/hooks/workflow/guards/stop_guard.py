"""Stop handler — blocks stoppage when the current story is not completed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import subprocess

from workflow.hook import Hook
from workflow.state_store import StateStore
from workflow.workflow_gate import check_workflow_gate
from workflow.config import get as cfg
from workflow.models.hook_input import StopInput
from workflow.constants.phases import STATUS_DONE


class StopGuard:
    def __init__(self, hook_input: StopInput):
        self._hook_input = hook_input
        self._is_workflow_active = check_workflow_gate()

    def is_story_completed(self) -> tuple[bool, str]:
        state = StateStore(state_path=cfg("paths.workflow_state"))
        story = state.get("story")
        if not story:
            return False, "Story not found"
        return story.get("status") == STATUS_DONE, story.get("id")

    def is_pr_created(self) -> bool:
        state = StateStore(state_path=cfg("paths.workflow_state"))
        return state.get("pr_created", False)

    def run(self) -> None:
        if not self._is_workflow_active:
            return

        is_completed, story_id = self.is_story_completed()

        if not is_completed:
            Hook.block(f"Story '{story_id}' is not completed.")

        if not self.is_pr_created():
            Hook.block("PR has not been created yet.")


if __name__ == "__main__":
    hook_input = StopInput.model_validate(Hook.read_stdin())
    StopGuard(hook_input).run()
