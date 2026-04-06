"""UserPromptSubmit handler — intercepts /build and prepares parallel implement prompts."""

import sys
from pathlib import Path

import re
import subprocess
import json


sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from build.hook import Hook
from build.lib.parallel_session import parallel_sessions


class BuildEntry:
    def __init__(self, raw_input: dict):
        self._raw_input = raw_input

    def validate_prompt(self) -> bool:
        return self._raw_input.get("prompt", "").startswith("/build")

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
                "ready",
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

        prompts = self.prompts
        if not prompts:
            return
        self.launch_sessions(prompts)
        Hook.advanced_output(
            {"continue": False, "reason": "No further action required"}
        )


def main() -> None:
    raw_input = Hook.read_stdin()
    build_entry = BuildEntry(raw_input)
    build_entry.run()


if __name__ == "__main__":
    main()
