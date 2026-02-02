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

Backward Compatibility:
The following imports are maintained for backward compatibility with
existing hooks that import directly from this module.
"""

# Backward compatible imports from state.py
from .state import (
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

# Backward compatible imports from phases.py
from .phases import (
    PHASES,
    TDD_PHASES,
    TA_PHASES,
    DEFAULT_PHASES,
    PHASE_SUBAGENTS,
    get_phase_order,
    get_all_phases,
)

# New architecture exports
from .core import (
    StateManager,
    PhaseEngine,
    DeliverablesTracker,
)

from .config import (
    WorkflowConfig,
    load_workflow_config,
    get_config,
    get_phases,
    get_deliverables,
    get_phase_subagents,
    get_phase_deliverables,
)

__all__ = [
    # Legacy state functions
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
    # Legacy phase constants
    "PHASES",
    "TDD_PHASES",
    "TA_PHASES",
    "DEFAULT_PHASES",
    "PHASE_SUBAGENTS",
    "get_phase_order",
    "get_all_phases",
    # New architecture
    "StateManager",
    "PhaseEngine",
    "DeliverablesTracker",
    "WorkflowConfig",
    "load_workflow_config",
    "get_config",
    "get_phases",
    "get_deliverables",
    "get_phase_subagents",
    "get_phase_deliverables",
]
