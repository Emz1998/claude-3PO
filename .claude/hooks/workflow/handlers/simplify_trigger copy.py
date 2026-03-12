"""PostToolUse handler — injects /simplify system message on new file creation during code phase."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import PostToolUseInput
from workflow.workflow_log import log


class SimplifyTrigger:
    def __init__(self, hook_input: PostToolUseInput):
        self._hook_input = hook_input

    def run(self) -> None:
        if not check_workflow_gate():
            log("SimplifyTrigger", "Skipped", "Workflow is not active")
            return

        # Only trigger on Write tool (new file creation)
        if self._hook_input.tool_name != "Write":
            log("SimplifyTrigger", "Skipped", "Tool name is not Write")
            return

        session_state = SessionState()
        story_id = session_state.story_id
        if not story_id:
            log("SimplifyTrigger", "Skipped", "Story ID is not set")
            return

        session = session_state.get_session(story_id)
        if not session:
            log("SimplifyTrigger", "Skipped", "Session is not found")
            return

        skill = self._hook_input.tool_input.skill

        if skill not in ["code", "simplify"]:
            log("SimplifyTrigger", "Skipped", "Skill is not code or simplify")
            return

        if skill == "code":

            Hook.advanced_output(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": "A new file was created. Review for reuse opportunities and simplification with /simplify.",
                    }
                }
            )
            return

        simplify_status = session.get("simplify", {}).get("status", "inactive")
        if simplify_status != "pending":
            log("SimplifyTrigger", "Skipped", "Simplify is not pending")
            return


if __name__ == "__main__":
    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())
    SimplifyTrigger(hook_input).run()
