"""UserPromptSubmit handler — intercepts /implement and starts a story."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import subprocess

from workflow.hook import Hook
from workflow.state_store import StateStore
from workflow.workflow_gate import activate_workflow
from workflow.models.hook_input import UserPromptSubmitInput
from workflow.config import get as cfg
from workflow.constants.phases import STATUS_IN_PROGRESS
from workflow.handlers.recorder import record_pre_coding_phase


class ImplementTrigger:
    def __init__(self, hook_input: UserPromptSubmitInput):
        self._hook_input = hook_input

    @staticmethod
    def parse_prompt(prompt: str) -> tuple[str, str]:
        parts = prompt.strip().split(" ")
        if len(parts) != 2:
            raise ValueError("Args shouldnt be more than 1")
        return parts[0], parts[1]

    @property
    def story_id(self) -> str:
        _, story_id = self.parse_prompt(self._hook_input.prompt)
        return story_id

    def validate_prompt(self) -> bool:
        return self._hook_input.prompt.startswith("/implement")

    def run(self) -> None:
        if not self.validate_prompt():
            return

        activate_workflow()
        record_pre_coding_phase()

        # Update story status
        result = subprocess.run(
            [
                "python",
                "github_project/project_manager.py",
                "update",
                self.story_id,
                "--status",
                STATUS_IN_PROGRESS,
                "--force",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            Hook.block(result.stderr.strip() or "Failed to start story")

        # Track which story this session is implementing
        state = StateStore(state_path=cfg("paths.workflow_state"))
        sessions = state.get("implement_sessions") or {}
        sessions[self._hook_input.session_id] = self.story_id
        state.set("implement_sessions", sessions)

        # Reset PR state for new story
        state.set("pr_created", False)

        # Render context via view
        result = subprocess.run(
            ["python", "github_project/project_manager.py", "view", self.story_id],
            capture_output=True,
            text=True,
        )
        Hook.success_response(result.stdout)


if __name__ == "__main__":
    hook_input = UserPromptSubmitInput.model_validate(Hook.read_stdin())
    implement_trigger = ImplementTrigger(hook_input)
    implement_trigger.run()
