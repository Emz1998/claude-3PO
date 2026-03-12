"""PostToolUse handler — removes worktree after CI green."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import PostToolUseInput
from workflow.constants.phases import CI_PASS


def remove_worktree(story_id: str) -> None:
    """Remove the git worktree for a story."""
    try:
        subprocess.run(
            ["git", "worktree", "remove", story_id, "--force"],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError:
        pass  # Worktree may not exist


class CleanupTrigger:
    def __init__(self, hook_input: PostToolUseInput):
        self._hook_input = hook_input

    def run(self) -> None:
        if not check_workflow_gate():
            return

        # Only trigger on /push skill
        if self._hook_input.tool_name != "Skill":
            return
        if self._hook_input.tool_input.skill != "push":
            return

        session_state = SessionState()
        story_id = session_state.story_id
        if not story_id:
            return

        session = session_state.get_session(story_id)
        if not session:
            return

        ci_status = session.get("ci", {}).get("status")
        if ci_status != CI_PASS:
            return

        remove_worktree(story_id)


if __name__ == "__main__":
    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())
    CleanupTrigger(hook_input).run()
