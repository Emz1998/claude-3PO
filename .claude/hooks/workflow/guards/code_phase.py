"""PreToolUse handler — validates coding phase agent ordering."""

from typing import Any, cast
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.models.hook_input import PreToolUseInput
from workflow.workflow_gate import check_workflow_gate
from workflow.utils.order_validation import validate_order
from workflow.config import get as cfg


class CodingPhaseGuard:
    TEST_AGENTS = cfg("agents.test")
    CODE_AGENTS = cfg("agents.code")

    def __init__(self, hook_input: PreToolUseInput):
        self._hook_input = hook_input
        self._session = SessionState()

    def _get_session_data(self, key: str, default: Any = None) -> Any:
        """Read a value from the current session."""
        story_id = self._session.story_id
        if not story_id:
            return default
        session = self._session.get_session(story_id)
        if not session:
            return default
        return session.get(key, default)

    def resolve_agents_list(self) -> list[str]:
        tdd = self._get_session_data("TDD", False)
        if tdd:
            return self.TEST_AGENTS + self.CODE_AGENTS
        return self.CODE_AGENTS

    def validate_transition(self) -> tuple[bool, str]:
        recent_agent = None
        story_id = self._session.story_id
        if story_id:
            session = self._session.get_session(story_id)
            if session:
                recent_agent = session.get("phase", {}).get("recent_agent")
        if not recent_agent:
            recent_agent = "Explore"

        hook_input = cast(PreToolUseInput, self._hook_input)
        return validate_order(
            recent_agent,
            hook_input.tool_input.subagent_type,
            self.resolve_agents_list(),
        )

    def run(self) -> None:
        is_workflow_active = check_workflow_gate()
        if not is_workflow_active:
            return

        is_valid, reason = self.validate_transition()
        if not is_valid:
            Hook.block(reason)


if __name__ == "__main__":
    hook_input = PreToolUseInput.model_validate(Hook.read_stdin())
    guard = CodingPhaseGuard(hook_input)
    guard.run()
