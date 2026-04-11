"""agent_guard.py — PreToolUse guard for Agent tool.

Validates agent invocation. Agent recording happens in subagent_start.py.
"""

from typing import Literal

from utils.validators import is_agent_allowed
from utils.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


def handle(hook_input: dict, config: Config, state: StateStore) -> Decision:
    try:
        allowed, message = is_agent_allowed(hook_input, config, state)
        return "allow", message
    except ValueError as e:
        return "block", str(e)
