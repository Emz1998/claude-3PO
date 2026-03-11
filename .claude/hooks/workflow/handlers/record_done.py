"""Stop handler — blocks stoppage when the current story is not completed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import subprocess

from workflow.hook import Hook
from workflow.state_store import StateStore
from workflow.workflow_gate import check_workflow_gate
from workflow.config import get as cfg
from workflow.models.hook_input import PostToolUseInput
from workflow.constants.phases import STATUS_DONE


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

        state = StateStore(state_path=cfg("paths.workflow_state"))
        state.set("story", {"id": _id, "status": status})


if __name__ == "__main__":
    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())
    RecordCompletion(hook_input).run()
