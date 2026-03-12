"""PreToolUse handler — validates workflow phase ordering."""

from typing import Any, Generic, TypeVar, cast
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.models.hook_input import PreToolUseInput, PostToolUseInput, StopInput
from workflow.workflow_gate import check_workflow_gate
from workflow.utils.order_validation import validate_order
from workflow.config import get as cfg


T = TypeVar("T", bound=PreToolUseInput | PostToolUseInput | StopInput)


class PreCodingPhaseGuard(Generic[T]):
    AGENTS = cfg("agents.pre_coding")

    def __init__(self, hook_input: T):
        self._session = SessionState()
        self._hook_input = hook_input

    def _get_recent_agent(self) -> str | None:
        """Read recent_agent from session state."""
        story_id = self._session.story_id
        if not story_id:
            return None
        session = self._session.get_session(story_id)
        if session:
            return session.get("phase", {}).get("recent_agent")
        return None

    def validate_transition(self) -> tuple[bool, str]:
        recent_agent = self._get_recent_agent() or "Explore"
        hook_input = cast(PreToolUseInput, self._hook_input)
        return validate_order(
            recent_agent, hook_input.tool_input.subagent_type, self.AGENTS
        )

    @property
    def is_plan_mode(self) -> bool:
        return self._hook_input.permission_mode == "plan"

    def run(self) -> None:
        is_workflow_active = check_workflow_gate()
        if not is_workflow_active:
            print("Workflow is not active")
            return
        if not self.is_plan_mode:
            print("Not in plan mode")
            return
        is_valid, reason = self.validate_transition()
        if not is_valid:
            print(reason)
            Hook.block(reason)


class PlanReviewPhaseGuard:
    def __init__(self, plan_file_path: Path, hook_input: PreToolUseInput):
        self._plan_file_path = plan_file_path
        self._hook_input = hook_input

    def validate_file_path(self) -> tuple[bool, str]:
        received_file_path = self._hook_input.tool_input.file_path
        if received_file_path != self._plan_file_path:
            return (
                False,
                f"Expected file path: {self._plan_file_path}, received: {received_file_path}",
            )
        return True, ""

    def run(self) -> None:
        is_edit_tool = self._hook_input.tool_name == "Edit"
        if not is_edit_tool:
            return

        is_valid, reason = self.validate_file_path()
        if not is_valid:
            Hook.block(reason)


if __name__ == "__main__":
    hook_input = PreToolUseInput.model_validate(Hook.read_stdin())
    phase_guard = PreCodingPhaseGuard(hook_input)
    phase_guard.run()
