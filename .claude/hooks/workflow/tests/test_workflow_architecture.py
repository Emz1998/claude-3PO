#!/usr/bin/env python3
"""Pytest tests for the workflow hooks architecture."""

import sys
from pathlib import Path

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.unified_loader import (  # type: ignore
    load_unified_config,
    get_agent_for_phase,
    get_phase_deliverables_typed,
    clear_unified_cache,
)
from core.state_manager import StateManager  # type: ignore
from core.phase_engine import PhaseEngine, get_phase_order  # type: ignore
from core.deliverables_tracker import DeliverablesTracker  # type: ignore
from guards.phase_transition import validate_phase_transition  # type: ignore
from guards.subagent_access import validate_subagent_access  # type: ignore


@pytest.fixture
def state_manager():
    """Provide a fresh state manager for each test."""
    manager = StateManager()
    manager.reset()
    yield manager
    manager.reset()


@pytest.fixture
def phase_engine():
    """Provide a TDD phase engine."""
    return PhaseEngine("tdd")


@pytest.fixture
def deliverables_tracker(state_manager):
    """Provide a deliverables tracker with initialized state."""
    return DeliverablesTracker(state_manager)


@pytest.fixture(autouse=True)
def clear_config_cache():
    """Clear config cache before and after each test."""
    clear_unified_cache()
    yield
    clear_unified_cache()


class TestConfigLoader:
    """Tests for the unified configuration loader module."""

    def test_load_unified_config_returns_dataclass(self):
        """Unified config loader returns a UnifiedWorkflowConfig."""
        config = load_unified_config(validate=False)
        assert hasattr(config, "phases")
        assert hasattr(config, "agents")
        assert hasattr(config, "deliverables")
        assert hasattr(config, "project")
        assert hasattr(config, "features")

    def test_config_has_phases(self):
        """Config contains phase definitions."""
        config = load_unified_config(validate=False)
        assert isinstance(config.phases, dict)
        assert "base" in config.phases

    def test_config_has_agents(self):
        """Config contains agent mappings."""
        config = load_unified_config(validate=False)
        assert isinstance(config.agents, dict)
        assert config.agents.get("explore") == "codebase-explorer"
        assert config.agents.get("commit") == "version-manager"

    def test_get_phase_deliverables_typed_returns_dataclass(self):
        """Phase deliverables returns a PhaseDeliverables dataclass."""
        deliverables = get_phase_deliverables_typed("explore")
        assert hasattr(deliverables, "read")
        assert hasattr(deliverables, "write")
        assert hasattr(deliverables, "edit")
        assert hasattr(deliverables, "bash")
        assert hasattr(deliverables, "skill")


class TestStateManager:
    """Tests for the state manager module."""

    def test_initial_state_inactive(self, state_manager):
        """Workflow is inactive after reset."""
        assert state_manager.is_workflow_active() is False

    def test_activate_workflow(self, state_manager):
        """Workflow can be activated."""
        state_manager.activate_workflow()
        assert state_manager.is_workflow_active() is True

    def test_deactivate_workflow(self, state_manager):
        """Workflow can be deactivated."""
        state_manager.activate_workflow()
        state_manager.deactivate_workflow()
        assert state_manager.is_workflow_active() is False

    def test_set_and_get_value(self, state_manager):
        """Values can be set and retrieved."""
        state_manager.set("test_key", "test_value")
        assert state_manager.get("test_key") == "test_value"

    def test_get_nonexistent_key_returns_none(self, state_manager):
        """Getting nonexistent key returns None."""
        assert state_manager.get("nonexistent_key") is None

    def test_set_overwrites_existing(self, state_manager):
        """Setting a key overwrites existing value."""
        state_manager.set("key", "first")
        state_manager.set("key", "second")
        assert state_manager.get("key") == "second"

    def test_reset_clears_all_state(self, state_manager):
        """Reset clears all state values."""
        state_manager.set("custom_key", "value")
        state_manager.activate_workflow()
        state_manager.reset()
        assert state_manager.is_workflow_active() is False
        assert state_manager.get("custom_key") is None


class TestPhaseEngine:
    """Tests for the phase engine module."""

    def test_valid_phase_recognized(self, phase_engine):
        """Valid phases are recognized."""
        assert phase_engine.is_valid_phase("explore")
        assert phase_engine.is_valid_phase("plan")
        assert phase_engine.is_valid_phase("commit")

    def test_invalid_phase_rejected(self, phase_engine):
        """Invalid phases are rejected."""
        assert not phase_engine.is_valid_phase("invalid-phase")
        assert not phase_engine.is_valid_phase("")
        assert not phase_engine.is_valid_phase(None)

    def test_valid_transition_from_none_to_explore(self, phase_engine):
        """Transition from None to explore is valid."""
        is_valid, error = phase_engine.is_valid_transition(None, "explore")
        assert is_valid
        assert error == ""

    def test_valid_transition_sequential(self, phase_engine):
        """Sequential phase transitions are valid."""
        is_valid, error = phase_engine.is_valid_transition("explore", "plan")
        assert is_valid
        assert error == ""

    def test_invalid_transition_skip_phase(self, phase_engine):
        """Skipping phases is invalid."""
        is_valid, error = phase_engine.is_valid_transition("explore", "commit")
        assert not is_valid
        assert "Must complete" in error

    def test_invalid_transition_backwards(self, phase_engine):
        """Going backwards is invalid."""
        is_valid, error = phase_engine.is_valid_transition("plan", "explore")
        assert not is_valid
        assert "Cannot go backwards" in error

    def test_get_phase_order_returns_list(self):
        """get_phase_order returns a list."""
        phases = get_phase_order("tdd")
        assert isinstance(phases, list)
        assert len(phases) > 0

    def test_phase_order_starts_with_explore(self):
        """Phase order starts with explore."""
        phases = get_phase_order("tdd")
        assert phases[0] == "explore"

    def test_phase_order_ends_with_commit(self):
        """Phase order ends with commit."""
        phases = get_phase_order("tdd")
        assert phases[-1] == "commit"


class TestDeliverablesTracker:
    """Tests for the deliverables tracker module."""

    def test_initialize_for_phase(self, deliverables_tracker):
        """Deliverables can be initialized for a phase."""
        deliverables_tracker.initialize_for_phase("explore")
        deliverables = deliverables_tracker.get_deliverables()
        assert isinstance(deliverables, list)

    def test_get_deliverables_returns_list(self, deliverables_tracker):
        """get_deliverables returns a list."""
        deliverables = deliverables_tracker.get_deliverables()
        assert isinstance(deliverables, list)

    def test_are_all_met_returns_tuple(self, deliverables_tracker):
        """are_all_met returns a tuple of (bool, str)."""
        deliverables_tracker.initialize_for_phase("explore")
        result = deliverables_tracker.are_all_met()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_empty_deliverables_are_met(self, state_manager):
        """Empty deliverables list means all are met."""
        state_manager.set("deliverables", [])
        tracker = DeliverablesTracker(state_manager)
        all_met, message = tracker.are_all_met()
        assert all_met

class TestSkillDeliverableType:
    """Tests for the skill deliverable type feature."""

    def test_skill_deliverable_marked_complete(self, state_manager):
        """Skill deliverable can be marked complete with invoke action."""
        state_manager.set_deliverables(
            [
                {
                    "type": "skill",
                    "action": "invoke",
                    "pattern": "^commit$",
                    "completed": False,
                }
            ]
        )
        result = state_manager.mark_deliverable_complete("invoke", "commit")
        assert result is True
        deliverables = state_manager.get_deliverables()
        assert deliverables[0]["completed"] is True

    def test_skill_deliverable_pattern_matching(self, state_manager):
        """Skill deliverable uses regex pattern matching."""
        state_manager.set_deliverables(
            [
                {
                    "type": "skill",
                    "action": "invoke",
                    "pattern": "^plan.*$",
                    "completed": False,
                }
            ]
        )
        result = state_manager.mark_deliverable_complete("invoke", "plan-consult")
        assert result is True

    def test_skill_deliverable_no_match(self, state_manager):
        """Non-matching skill name does not mark deliverable complete."""
        state_manager.set_deliverables(
            [
                {
                    "type": "skill",
                    "action": "invoke",
                    "pattern": "^commit$",
                    "completed": False,
                }
            ]
        )
        result = state_manager.mark_deliverable_complete("invoke", "explore")
        assert result is False
        deliverables = state_manager.get_deliverables()
        assert deliverables[0]["completed"] is False


class TestGuards:
    """Tests for guard modules."""

    def test_phase_transition_valid_initial(self):
        """Initial transition to explore is valid."""
        is_valid, error = validate_phase_transition(None, "explore")
        assert is_valid

    def test_phase_transition_invalid_skip(self):
        """Skipping phases is invalid."""
        is_valid, error = validate_phase_transition("explore", "commit")
        assert not is_valid
        assert error != ""

    def test_subagent_access_valid_mapping(self):
        """Correct subagent for phase is valid."""
        is_valid, error = validate_subagent_access("explore", "codebase-explorer")
        assert is_valid

    def test_subagent_access_invalid_mapping(self):
        """Wrong subagent for phase is invalid."""
        is_valid, error = validate_subagent_access("explore", "wrong-agent")
        assert not is_valid
        assert error != ""


class TestBackwardCompatibility:
    """Tests for backward compatible imports."""

    def test_import_from_workflow_module(self):
        """Core imports from workflow module work."""
        from workflow import (  # type: ignore
            load_state,
            save_state,
            get_state,
            set_state,
            get_phase_order,
        )

        assert callable(load_state)
        assert callable(save_state)
        assert callable(get_state)
        assert callable(set_state)
        assert callable(get_phase_order)

    def test_import_new_architecture_from_workflow(self):
        """New architecture imports from workflow module work."""
        from workflow import (  # type: ignore
            StateManager,
            PhaseEngine,
            DeliverablesTracker,
        )

        assert StateManager is not None
        assert PhaseEngine is not None
        assert DeliverablesTracker is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
