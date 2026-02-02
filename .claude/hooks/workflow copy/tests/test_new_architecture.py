#!/usr/bin/env python3
"""Tests for the new workflow architecture."""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_config_loader():
    """Test config module loads correctly."""
    from config.loader import (  # type: ignore
        load_workflow_config,
        get_phases,
        get_phase_subagents,
    )

    config = load_workflow_config()
    assert "phases" in config
    assert "subagents" in config
    assert "deliverables" in config

    phases = get_phases("tdd")
    assert "explore" in phases
    assert "commit" in phases
    assert "write-test" in phases

    subagents = get_phase_subagents()
    assert subagents.get("explore") == "codebase-explorer"
    assert subagents.get("commit") == "version-manager"

    print("Config loader tests passed")


def test_state_manager():
    """Test state manager works correctly."""
    from core.state_manager import StateManager  # type: ignore

    manager = StateManager()
    manager.reset()

    assert manager.is_workflow_active() is False
    manager.activate_workflow()
    assert manager.is_workflow_active() is True
    manager.deactivate_workflow()
    assert manager.is_workflow_active() is False

    manager.set("test_key", "test_value")
    assert manager.get("test_key") == "test_value"

    print("State manager tests passed")


def test_phase_engine():
    """Test phase engine works correctly."""
    from core.phase_engine import (  # type: ignore
        PhaseEngine,
        get_phase_order,
        validate_order,
    )

    engine = PhaseEngine("tdd")

    assert engine.is_valid_phase("explore")
    assert engine.is_valid_phase("commit")
    assert not engine.is_valid_phase("invalid-phase")

    # Valid transitions
    is_valid, _ = engine.is_valid_transition(None, "explore")
    assert is_valid

    is_valid, _ = engine.is_valid_transition("explore", "plan")
    assert is_valid

    # Invalid transitions
    is_valid, error = engine.is_valid_transition("explore", "commit")
    assert not is_valid
    assert "Must complete" in error

    is_valid, error = engine.is_valid_transition("plan", "explore")
    assert not is_valid
    assert "Cannot go backwards" in error

    print("Phase engine tests passed")


def test_deliverables_tracker():
    """Test deliverables tracker works correctly."""
    from core.state_manager import StateManager  # type: ignore
    from core.deliverables_tracker import DeliverablesTracker  # type: ignore

    manager = StateManager()
    manager.reset()

    tracker = DeliverablesTracker(manager)
    tracker.initialize_for_phase("explore")

    deliverables = tracker.get_deliverables()
    assert isinstance(deliverables, list)

    all_met, message = tracker.are_all_met()
    if deliverables:
        assert not all_met  # Should have incomplete deliverables
    else:
        assert all_met  # No deliverables means all met

    print("Deliverables tracker tests passed")


def test_guards():
    """Test guards work correctly."""
    from guards.phase_transition import validate_phase_transition  # type: ignore
    from guards.subagent_access import validate_subagent_access  # type: ignore

    # Phase transition
    is_valid, _ = validate_phase_transition(None, "explore")
    assert is_valid

    is_valid, error = validate_phase_transition("explore", "commit")
    assert not is_valid

    # Subagent access
    is_valid, _ = validate_subagent_access("explore", "codebase-explorer")
    assert is_valid

    is_valid, error = validate_subagent_access("explore", "wrong-agent")
    assert not is_valid

    print("Guards tests passed")


def run_all_tests():
    """Run all tests."""
    print("Running new architecture tests...\n")

    try:
        test_config_loader()
    except Exception as e:
        print(f"Config loader test failed: {e}")

    try:
        test_state_manager()
    except Exception as e:
        print(f"State manager test failed: {e}")

    try:
        test_phase_engine()
    except Exception as e:
        print(f"Phase engine test failed: {e}")

    try:
        test_deliverables_tracker()
    except Exception as e:
        print(f"Deliverables tracker test failed: {e}")

    try:
        test_guards()
    except Exception as e:
        print(f"Guards test failed: {e}")

    print("\nAll tests completed!")


if __name__ == "__main__":
    run_all_tests()
