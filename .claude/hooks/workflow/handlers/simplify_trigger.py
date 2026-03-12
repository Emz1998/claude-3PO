"""PostToolUse handler — injects /simplify system message on new file creation during code phase."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.hook import Hook
from workflow.session_state import SessionState
from workflow.workflow_gate import check_workflow_gate
from workflow.models.hook_input import PostToolUseInput


class SimplifyTrigger:
    def __init__(self, hook_input: PostToolUseInput):
        self._hook_input = hook_input

    def run(self) -> None:
        if not check_workflow_gate():
            return

        # Only trigger on Write tool (new file creation)
        if self._hook_input.tool_name != "Write":
            return

        session_state = SessionState()
        story_id = session_state.story_id
        if not story_id:
            return

        session = session_state.get_session(story_id)
        if not session:
            return

        current_phase = session.get("phase", {}).get("current", "")
        if current_phase != "code":
            return

        Hook.advanced_output({
            "systemMessage": "A new file was created. Review for reuse opportunities and simplification with /simplify."
        })


if __name__ == "__main__":
    hook_input = PostToolUseInput.model_validate(Hook.read_stdin())
    SimplifyTrigger(hook_input).run()
