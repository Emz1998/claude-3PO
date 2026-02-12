#!/usr/bin/env python3
"""Workflow orchestration module for Claude hooks.

This module provides workflow state management, phase tracking, deliverables
enforcement, and context injection for the /implement workflow.

Architecture:
- config/: Unified configuration (YAML + typed loader)
- core/: State management, phase engine, deliverables tracker
- guards/: PreToolUse validation hooks
- trackers/: PostToolUse tracking hooks
- context/: Phase-specific context injection
- handlers/: Consolidated hook entry points
- release_plan/: Release plan state management
"""

# State management
from .core.state_manager import (
    load_state,
    save_state,
    get_state,
    set_state,
    initialize_state,
    reset_state,
    initialize_deliverables_state,
    reset_deliverables_state,
    get_deliverable_state,
    mark_deliverable_complete,
    are_all_deliverables_met,
    add_deliverable,
    reset_deliverables_status,
)

# Phase engine
from .core.phase_engine import (
    get_phase_order,
    get_all_phases,
)

# Core classes
from .core import (
    StateManager,
    PhaseEngine,
    DeliverablesTracker,
)

__all__ = [
    # State functions
    "load_state",
    "save_state",
    "get_state",
    "set_state",
    "initialize_state",
    "reset_state",
    "initialize_deliverables_state",
    "reset_deliverables_state",
    "get_deliverable_state",
    "mark_deliverable_complete",
    "are_all_deliverables_met",
    "add_deliverable",
    "reset_deliverables_status",
    # Phase functions
    "get_phase_order",
    "get_all_phases",
    # Core classes
    "StateManager",
    "PhaseEngine",
    "DeliverablesTracker",
]
