#!/usr/bin/env python3
"""Core module for workflow state and phase management.

Contains the fundamental building blocks for workflow orchestration:
- StateManager: Unified API for workflow state operations
- PhaseEngine: Phase definitions, ordering, and transitions
- DeliverablesTracker: Deliverable initialization and completion tracking
"""

from .state_manager import StateManager
from .phase_engine import (
    PhaseEngine,
    get_phase_order,
    get_phase_subagent,
    is_valid_transition,
)
from .deliverables_tracker import (
    DeliverablesTracker,
    initialize_deliverables,
    mark_deliverable_complete,
    are_all_deliverables_met,
)

__all__ = [
    # State Manager
    "StateManager",
    # Phase Engine
    "PhaseEngine",
    "get_phase_order",
    "get_phase_subagent",
    "is_valid_transition",
    # Deliverables Tracker
    "DeliverablesTracker",
    "initialize_deliverables",
    "mark_deliverable_complete",
    "are_all_deliverables_met",
]
