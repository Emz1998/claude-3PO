"""command_guard.py — PreToolUse guard for Bash tool.

Validates commands against phase restrictions.
Records test execution and PR/CI outputs when applicable.
"""

from typing import Literal

from utils.validators import is_command_allowed, is_test_executed
from utils.recorder import record_test_execution
from utils.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


def handle(hook_input: dict, config: Config, state: StateStore) -> Decision:
    try:
        allowed, message = is_command_allowed(hook_input, config, state)

        command = hook_input.get("tool_input", {}).get("command", "")
        phase = state.current_phase

        # Record test execution if a test command runs in write-tests or test-review
        if phase in ("write-tests", "test-review"):
            try:
                is_test_executed(command)
                record_test_execution(state)
            except ValueError:
                pass  # Not a test command, that's fine

        return "allow", message
    except ValueError as e:
        return "block", str(e)
