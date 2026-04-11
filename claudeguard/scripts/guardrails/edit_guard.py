"""edit_guard.py — PreToolUse guard for Edit tool.

Validates file edit is allowed for the current phase and file path.
"""

from typing import Literal

from utils.validators import is_file_edit_allowed
from utils.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


def handle(hook_input: dict, config: Config, state: StateStore) -> Decision:
    try:
        allowed, message = is_file_edit_allowed(hook_input, config, state)
        if allowed:
            phase = state.current_phase
            file_path = hook_input.get("tool_input", {}).get("file_path", "")
            if phase == "plan-review":
                state.set_plan_revised(True)
            elif phase == "test-review" and file_path:
                state.add_test_file_revised(file_path)
            elif phase == "code-review" and file_path:
                if file_path in state.code_tests_to_revise:
                    state.add_code_test_revised(file_path)
                else:
                    state.add_file_revised(file_path)
        return "allow", message
    except ValueError as e:
        return "block", str(e)
