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
        return "allow", message
    except ValueError as e:
        return "block", str(e)
