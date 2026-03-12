"""PreToolUse guard — restricts dangerous bash commands by workflow phase.

Rules:
- gh pr create → BLOCK unless phase == "create-pr"
- gh pr (close|merge|edit) → BLOCK always
- git push → BLOCK unless phase == "push"
- Everything else → ALLOW
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import PreToolUseInput


# Always-blocked PR operations
_BLOCKED_PR_OPS = re.compile(r"gh\s+pr\s+(close|merge|edit)")
# Phase-gated operations
_GH_PR_CREATE = re.compile(r"gh\s+pr\s+create")
_GIT_PUSH = re.compile(r"git\s+push")


class BashGuard:
    def __init__(self, hook_input: PreToolUseInput):
        self._hook_input = hook_input

    def run(self) -> None:
        if not check_workflow_gate():
            return

        session_state = SessionState()
        story_id = session_state.story_id
        if not story_id:
            return

        session = session_state.get_session(story_id)
        if not session:
            return

        command = self._hook_input.tool_input.command
        current_phase = session.get("phase", {}).get("current", "")

        # Always-blocked operations
        if _BLOCKED_PR_OPS.search(command):
            Hook.block("gh pr close/merge/edit is not allowed.")

        # Phase-gated: gh pr create
        if _GH_PR_CREATE.search(command) and current_phase != "create-pr":
            Hook.block(f"gh pr create is only allowed in 'create-pr' phase (current: '{current_phase}').")

        # Phase-gated: git push
        if _GIT_PUSH.search(command) and current_phase != "push":
            Hook.block(f"git push is only allowed in 'push' phase (current: '{current_phase}').")


if __name__ == "__main__":
    hook_input = PreToolUseInput.model_validate(Hook.read_stdin())
    BashGuard(hook_input).run()
