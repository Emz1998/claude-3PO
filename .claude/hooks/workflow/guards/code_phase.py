"""PreToolUse handler — validates workflow phase ordering."""

from typing import cast
from pathlib import Path

from workflow.state_store import StateStore
from workflow.hook import Hook
from workflow.models.hook_input import PreToolUseInput
from workflow.workflow_gate import check_workflow_gate
from workflow.utils.order_validation import validate_order
from workflow.config import get as cfg


STATE_PATH = Path(cfg("paths.workflow_state"))


class CodingPhaseGuard:
    TEST_AGENTS = cfg("agents.test")
    CODE_AGENTS = cfg("agents.code")

    def __init__(self, hook_input: PreToolUseInput):
        self._hook_input = hook_input
        self._state = StateStore(STATE_PATH)

    def resolve_agents_list(self) -> list[str]:
        if self._state.get("TDD", False):
            return self.TEST_AGENTS + self.CODE_AGENTS
        return self.CODE_AGENTS

    def validate_transition(self) -> tuple[bool, str]:
        recent_phase = self._state.get("recent_phase", "Explore")
        hook_input = cast(PreToolUseInput, self._hook_input)
        return validate_order(
            recent_phase,
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


# if __name__ == "__main__":
#     hook_input = PreToolUseInput.model_validate(Hook.read_stdin())
#     phase_guard = PreCodingPhaseGuard(hook_input)
#     phase_guard.run()
