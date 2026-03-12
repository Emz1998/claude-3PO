"""PostToolUse handler — records PR creation when gh pr create is detected."""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
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
        if "gh pr create" not in command:
            return

        session = SessionState()
        story_id = session.story_id
        if not story_id:
            return

        # Extract PR number from tool response if available
        pr_number = None
        response = getattr(self._hook_input, "tool_response", None)
        if response:
            content = response.get("content", "") if isinstance(response, dict) else str(response)
            match = re.search(r"/pull/(\d+)", content)
            if match:
                pr_number = int(match.group(1))

        try:
            def update_pr(s: dict) -> None:
                s["pr"]["created"] = True
                if pr_number:
                    s["pr"]["number"] = pr_number

            session.update_session(story_id, update_pr)
        except KeyError:
            pass


if __name__ == "__main__":
    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())
    PrRecorder(hook_input).run()
