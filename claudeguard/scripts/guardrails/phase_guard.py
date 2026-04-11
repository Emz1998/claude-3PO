"""phase_guard.py — PreToolUse guard for Skill (phase transition).

Validates phase ordering and records the transition.
"""

from typing import Literal

from utils.validators import is_phase_allowed
from utils.recorder import record_phase_transition
from utils.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


def handle(hook_input: dict, config: Config, state: StateStore) -> Decision:
    try:
        allowed, message = is_phase_allowed(hook_input, config, state)
        if allowed:
            next_phase = hook_input.get("tool_input", {}).get("skill", "")
            record_phase_transition(next_phase, state)
        return "allow", message
    except ValueError as e:
        return "block", str(e)
