#!/usr/bin/env python3
"""State machine for /implement workflow guardrail.

Tracks workflow progression through states:
- IDLE -> IMPLEMENT_ACTIVE -> TODO_READ -> EXPLORER_DONE -> PLANNER_DONE -> CONSULTANT_DONE
- Then enters coding phase: TDD, TA, or DEFAULT workflows
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import load_cache, write_cache  # type: ignore

# Cache keys for implement workflow
CACHE_KEY_ACTIVE = "implement_workflow_active"
CACHE_KEY_STATE = "implement_workflow_state"
CACHE_KEY_TODO_PATH = "implement_todo_path"
CACHE_KEY_CODING_MODE = "implement_coding_mode"
CACHE_KEY_CODING_STEP = "implement_coding_step"

# State constants
STATE_IDLE = "IDLE"
STATE_IMPLEMENT_ACTIVE = "IMPLEMENT_ACTIVE"
STATE_TODO_READ = "TODO_READ"
STATE_EXPLORER_DONE = "EXPLORER_DONE"
STATE_PLANNER_DONE = "PLANNER_DONE"
STATE_CONSULTANT_DONE = "CONSULTANT_DONE"

# Coding mode constants
CODING_MODE_TDD = "tdd"
CODING_MODE_TA = "ta"
CODING_MODE_DEFAULT = "default"

# TDD workflow states (5 steps)
TDD_STATES = [
    "CODING_TDD_1",  # Test engineer creating failing tests
    "CODING_TDD_2",  # Version manager commit tests
    "CODING_TDD_3",  # Engineer implementing to pass tests
    "CODING_TDD_4",  # Code reviewer review and iterate
    "CODING_TDD_5",  # Version manager final commit
]

# TA workflow states (4 steps)
TA_STATES = [
    "CODING_TA_1",  # Engineer implementing
    "CODING_TA_2",  # Test engineer creating tests
    "CODING_TA_3",  # Code reviewer
    "CODING_TA_4",  # Version manager commit
]

# Default workflow states (3 steps)
DEFAULT_STATES = [
    "CODING_DEFAULT_1",  # Engineer implementing
    "CODING_DEFAULT_2",  # Code/QA review
    "CODING_DEFAULT_3",  # Version manager commit
]

# Valid state transitions
STATE_TRANSITIONS = {
    STATE_IDLE: [STATE_IMPLEMENT_ACTIVE],
    STATE_IMPLEMENT_ACTIVE: [STATE_TODO_READ],
    STATE_TODO_READ: [STATE_EXPLORER_DONE],
    STATE_EXPLORER_DONE: [STATE_PLANNER_DONE],
    STATE_PLANNER_DONE: [STATE_CONSULTANT_DONE],
    STATE_CONSULTANT_DONE: ["CODING_TDD_1", "CODING_TA_1", "CODING_DEFAULT_1"],
}

# Add TDD transitions
for i in range(len(TDD_STATES) - 1):
    STATE_TRANSITIONS[TDD_STATES[i]] = [TDD_STATES[i + 1]]
STATE_TRANSITIONS[TDD_STATES[-1]] = [STATE_IDLE]

# Add TA transitions
for i in range(len(TA_STATES) - 1):
    STATE_TRANSITIONS[TA_STATES[i]] = [TA_STATES[i + 1]]
STATE_TRANSITIONS[TA_STATES[-1]] = [STATE_IDLE]

# Add Default transitions
for i in range(len(DEFAULT_STATES) - 1):
    STATE_TRANSITIONS[DEFAULT_STATES[i]] = [DEFAULT_STATES[i + 1]]
STATE_TRANSITIONS[DEFAULT_STATES[-1]] = [STATE_IDLE]


def is_workflow_active() -> bool:
    """Check if implement workflow is currently active."""
    cache = load_cache()
    return cache.get(CACHE_KEY_ACTIVE, False) is True


def get_current_state() -> str:
    """Get current workflow state."""
    cache = load_cache()
    return cache.get(CACHE_KEY_STATE, STATE_IDLE)


def get_coding_mode() -> str:
    """Get current coding mode (tdd, ta, or default)."""
    cache = load_cache()
    return cache.get(CACHE_KEY_CODING_MODE, CODING_MODE_DEFAULT)


def get_todo_path() -> Optional[str]:
    """Get the path to the todo file that was read."""
    cache = load_cache()
    return cache.get(CACHE_KEY_TODO_PATH)


def set_state(new_state: str) -> bool:
    """Set workflow state. Returns True if valid transition."""
    cache = load_cache()
    current_state = cache.get(CACHE_KEY_STATE, STATE_IDLE)

    # Validate transition
    valid_next_states = STATE_TRANSITIONS.get(current_state, [])
    if new_state not in valid_next_states and new_state != current_state:
        return False

    cache[CACHE_KEY_STATE] = new_state
    write_cache(cache)
    return True


def activate_workflow() -> None:
    """Activate the implement workflow (reset and start fresh)."""
    cache = load_cache()
    cache[CACHE_KEY_ACTIVE] = True
    cache[CACHE_KEY_STATE] = STATE_IMPLEMENT_ACTIVE
    cache[CACHE_KEY_TODO_PATH] = None
    cache[CACHE_KEY_CODING_MODE] = CODING_MODE_DEFAULT
    cache[CACHE_KEY_CODING_STEP] = 0
    write_cache(cache)


def deactivate_workflow() -> None:
    """Deactivate the implement workflow."""
    cache = load_cache()
    cache[CACHE_KEY_ACTIVE] = False
    cache[CACHE_KEY_STATE] = STATE_IDLE
    cache[CACHE_KEY_TODO_PATH] = None
    cache[CACHE_KEY_CODING_MODE] = CODING_MODE_DEFAULT
    cache[CACHE_KEY_CODING_STEP] = 0
    write_cache(cache)


def set_todo_read(todo_path: str) -> None:
    """Mark todo file as read and transition to TODO_READ state."""
    cache = load_cache()
    if cache.get(CACHE_KEY_STATE) == STATE_IMPLEMENT_ACTIVE:
        cache[CACHE_KEY_STATE] = STATE_TODO_READ
        cache[CACHE_KEY_TODO_PATH] = todo_path
        write_cache(cache)


def set_coding_mode(mode: str) -> None:
    """Set the coding mode (tdd, ta, or default)."""
    cache = load_cache()
    if mode in [CODING_MODE_TDD, CODING_MODE_TA, CODING_MODE_DEFAULT]:
        cache[CACHE_KEY_CODING_MODE] = mode
        write_cache(cache)


def start_coding_phase() -> None:
    """Start the coding phase based on current coding mode."""
    cache = load_cache()
    mode = cache.get(CACHE_KEY_CODING_MODE, CODING_MODE_DEFAULT)

    if mode == CODING_MODE_TDD:
        cache[CACHE_KEY_STATE] = TDD_STATES[0]
    elif mode == CODING_MODE_TA:
        cache[CACHE_KEY_STATE] = TA_STATES[0]
    else:
        cache[CACHE_KEY_STATE] = DEFAULT_STATES[0]

    cache[CACHE_KEY_CODING_STEP] = 1
    write_cache(cache)


def advance_coding_step() -> bool:
    """Advance to next coding step. Returns True if advanced, False if completed."""
    cache = load_cache()
    current_state = cache.get(CACHE_KEY_STATE, STATE_IDLE)

    # Find next state
    next_states = STATE_TRANSITIONS.get(current_state, [])
    if not next_states:
        return False

    next_state = next_states[0]
    cache[CACHE_KEY_STATE] = next_state

    # Check if workflow is complete (back to IDLE)
    if next_state == STATE_IDLE:
        cache[CACHE_KEY_ACTIVE] = False
        cache[CACHE_KEY_CODING_STEP] = 0
    else:
        cache[CACHE_KEY_CODING_STEP] = cache.get(CACHE_KEY_CODING_STEP, 0) + 1

    write_cache(cache)
    return next_state != STATE_IDLE


def is_in_coding_phase() -> bool:
    """Check if currently in a coding phase."""
    state = get_current_state()
    return state.startswith("CODING_")


def get_expected_subagent_for_state(state: str) -> list[str]:
    """Get the expected subagent types for a given state."""
    # Pre-coding phase
    if state == STATE_TODO_READ:
        return ["codebase-explorer"]
    elif state == STATE_EXPLORER_DONE:
        return ["planning-specialist"]
    elif state == STATE_PLANNER_DONE:
        return ["plan-consultant"]
    elif state == STATE_CONSULTANT_DONE:
        return []  # Transition to coding

    # TDD workflow
    elif state == "CODING_TDD_1":
        return ["test-engineer"]
    elif state == "CODING_TDD_2":
        return ["version-manager"]
    elif state == "CODING_TDD_3":
        return ["frontend-engineer", "backend-engineer", "fullstack-developer"]
    elif state == "CODING_TDD_4":
        return ["code-reviewer"]
    elif state == "CODING_TDD_5":
        return ["version-manager"]

    # TA workflow
    elif state == "CODING_TA_1":
        return ["frontend-engineer", "backend-engineer", "fullstack-developer"]
    elif state == "CODING_TA_2":
        return ["test-engineer"]
    elif state == "CODING_TA_3":
        return ["code-reviewer"]
    elif state == "CODING_TA_4":
        return ["version-manager"]

    # Default workflow
    elif state == "CODING_DEFAULT_1":
        return ["frontend-engineer", "backend-engineer", "fullstack-developer"]
    elif state == "CODING_DEFAULT_2":
        return ["code-reviewer"]
    elif state == "CODING_DEFAULT_3":
        return ["version-manager"]

    return []
