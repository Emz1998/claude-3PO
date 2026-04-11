"""webfetch_guard.py — PreToolUse guard for WebFetch tool.

Validates that the URL targets a safe domain.
"""

from typing import Literal

from utils.validators import is_webfetch_allowed
from utils.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


def handle(hook_input: dict, config: Config, state: StateStore) -> Decision:
    try:
        _, message = is_webfetch_allowed(hook_input, config, state)
        return "allow", message
    except ValueError as e:
        return "block", str(e)
