"""write_guard.py — PreToolUse guard for Write tool.

Validates file write is allowed, then records the file write.
"""

from typing import Literal

from utils.validators import is_file_write_allowed
from utils.recorder import record_file_write
from utils.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


def handle(hook_input: dict, config: Config, state: StateStore) -> Decision:
    try:
        allowed, message = is_file_write_allowed(hook_input, config, state)
        if allowed:
            record_file_write(hook_input, state)
        return "allow", message
    except ValueError as e:
        return "block", str(e)
