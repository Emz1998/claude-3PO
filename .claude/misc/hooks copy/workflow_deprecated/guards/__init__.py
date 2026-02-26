#!/usr/bin/env python3
"""Guards module for PreToolUse validation hooks.

Contains guardrails that validate operations before they execute:
- phase_transition: Validates phase transitions follow defined order
- subagent_access: Validates correct subagent for current phase
- deliverables_exit: Blocks exit if deliverables incomplete
- task_dod_stop: Blocks stop if tasks incomplete
"""

from .phase_transition import validate_phase_transition, PhaseTransitionGuard
from .subagent_access import validate_subagent_access, SubagentAccessGuard
from .deliverables_exit import validate_deliverables_exit, DeliverablesExitGuard
from .task_dod_stop import TaskDodStopGuard

__all__ = [
    # Phase Transition
    "validate_phase_transition",
    "PhaseTransitionGuard",
    # Subagent Access
    "validate_subagent_access",
    "SubagentAccessGuard",
    # Deliverables Exit
    "validate_deliverables_exit",
    "DeliverablesExitGuard",
    # Task DoD Stop
    "TaskDodStopGuard",
]
