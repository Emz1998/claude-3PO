"""phase_guard.py — PreToolUse guard for Skill (phase transition).

Validates phase ordering and records the transition.
"""

from typing import Literal

from utils.validators import is_phase_allowed
from utils.recorder import record_phase_transition
from utils.extractors import extract_skill_name
from utils.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


def handle(hook_input: dict, config: Config, state: StateStore) -> Decision:
    try:
        allowed, message = is_phase_allowed(hook_input, config, state)
        if allowed:
            next_phase = extract_skill_name(hook_input)
            # These skills modify the current phase — they don't add new ones
            if next_phase not in ("continue", "revise-plan", "plan-approved", "reset-plan-review"):
                current = state.current_phase
                parallel = current == "explore" and next_phase == "research"
                record_phase_transition(next_phase, state, parallel=parallel)
        return "allow", message
    except ValueError as e:
        return "block", str(e)
