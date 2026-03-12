"""UserPromptSubmit handler — creates PR review session from /review prompt."""

import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import activate_workflow
from workflow.models.hook_input import UserPromptSubmitInput
from workflow.workflow_log import log

_REVIEW_PATTERN = re.compile(r"/review\s+(\d+)")


class ReviewTrigger:
    def __init__(self, hook_input: UserPromptSubmitInput):
        self._hook_input = hook_input

    def run(self) -> None:
        activate_workflow()

        match = _REVIEW_PATTERN.search(self._hook_input.prompt)
        if not match:
            log("ReviewTrigger", "Skipped", "No PR number found")
            return

        pr_number = int(match.group(1))
        story_id = f"PR-{pr_number}"
        session_id = str(uuid.uuid4())

        session_state = SessionState()
        session_data = SessionState.default_pr_review_session(pr_number, session_id)
        session_state.create_session(story_id, session_data)

        log("ReviewTrigger", "Created", f"Review session created for PR #{pr_number}")


if __name__ == "__main__":
    hook_input = UserPromptSubmitInput.model_validate(Hook.read_stdin())
    ReviewTrigger(hook_input).run()
