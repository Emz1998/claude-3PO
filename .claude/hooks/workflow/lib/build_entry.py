"""UserPromptSubmit handler — intercepts /build and prepares parallel implement prompts."""

import sys
from pathlib import Path

import re
import subprocess
import json


sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.models.hook_input import UserPromptSubmitInput
from workflow.lib.parallel_session import parallel_sessions
from workflow.constants.phases import STATUS_READY


class BuildEntry:
    def __init__(self, hook_input: UserPromptSubmitInput):
        self._hook_input = hook_input

    def validate_prompt(self) -> bool:
        return self._hook_input.prompt.startswith("/build")

    @staticmethod
    def _get_open_prs() -> list[str]:
        """Return list of open PR numbers by running pr_manager.py list --active."""
        result = subprocess.run(
            ["python", "github_project/pr_manager.py", "list", "--active"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        return re.findall(r"PR #(\d+):", result.stdout)

    @property
    def prompts(self) -> list[str]:
        open_prs = self._get_open_prs()
        if open_prs:
            return [f"/review {pr_number}" for pr_number in open_prs]

        result = subprocess.run(
            [
                "python",
                "github_project/project_manager.py",
                "list",
                "--status",
                STATUS_READY,
                "-k",
            ],
            capture_output=True,
            text=True,
        )
        keys = result.stdout.strip()
        if not keys:
            return []
        story_ids = [
            s.strip() for s in keys.split(",") if not s.strip().startswith("T-")
        ]
        return [f"/implement {sid}" for sid in story_ids]

    @staticmethod
    def launch_sessions(prompts: list[str]) -> None:
        parallel_sessions(prompts)

    def run(self) -> None:
        if not self.validate_prompt():
            return

        activate_workflow()
        prompts = self.prompts
        if not prompts:
            return
        self.launch_sessions(prompts)
        Hook.advanced_output(
            {"continue": False, "reason": "No further action required"}
        )


if __name__ == "__main__":
    hook_input = UserPromptSubmitInput.model_validate(Hook.read_stdin())
    build_entry = BuildEntry(hook_input)
    build_entry.run()
