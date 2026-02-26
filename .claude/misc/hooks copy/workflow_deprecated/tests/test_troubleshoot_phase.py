#!/usr/bin/env python3
"""Tests for troubleshoot phase bypass functionality."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.unified_loader import (
    is_bypass_phase,
    can_bypass_from,
    get_bypass_config,
    clear_unified_cache,
)
from core.phase_engine import PhaseEngine, get_engine
from core.state_manager import StateManager


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear config cache before each test."""
    clear_unified_cache()
    yield
    clear_unified_cache()


@pytest.fixture
def state_manager(tmp_path):
    """Create a state manager with temp file."""
    state_path = tmp_path / "state.json"
    manager = StateManager(state_path)
    manager.reset()
    return manager


@pytest.fixture
def phase_engine():
    """Create a phase engine."""
    return PhaseEngine("tdd")


class TestBypassPhaseConfig:
    """Tests for bypass phase configuration."""

    def test_troubleshoot_is_bypass_phase(self):
        """Verify troubleshoot is identified as a bypass phase."""
        assert is_bypass_phase("troubleshoot") is True

    def test_regular_phases_not_bypass(self):
        """Verify regular phases are not bypass phases."""
        assert is_bypass_phase("explore") is False
        assert is_bypass_phase("plan") is False
        assert is_bypass_phase("write-code") is False

    def test_get_bypass_config_returns_config(self):
        """Verify bypass config is returned for troubleshoot."""
        config = get_bypass_config("troubleshoot")
        assert config is not None
        assert "write-code" in config.can_bypass
        assert "explore" in config.cannot_bypass

    def test_get_bypass_config_returns_none_for_regular(self):
        """Verify None is returned for non-bypass phases."""
        assert get_bypass_config("explore") is None
        assert get_bypass_config("write-code") is None


class TestCanBypassFrom:
    """Tests for can_bypass_from function."""

    def test_can_bypass_from_coding_phases(self):
        """Verify troubleshoot can bypass from coding phases."""
        coding_phases = [
            "write-tests",
            "review-tests",
            "write-code",
            "code-review",
            "refactor",
            "validate",
            "commit",
        ]
        for phase in coding_phases:
            assert (
                can_bypass_from("troubleshoot", phase) is True
            ), f"Should bypass from {phase}"

    def test_cannot_bypass_from_pre_coding_phases(self):
        """Verify troubleshoot cannot bypass from pre-coding phases."""
        pre_coding_phases = ["explore", "plan", "plan-consult", "finalize-plan"]
        for phase in pre_coding_phases:
            assert (
                can_bypass_from("troubleshoot", phase) is False
            ), f"Should not bypass from {phase}"

    def test_cannot_bypass_non_bypass_phase(self):
        """Verify non-bypass phases cannot bypass."""
        assert can_bypass_from("write-code", "explore") is False


class TestPhaseEngineBypass:
    """Tests for PhaseEngine bypass logic."""

    def test_is_bypass_phase_method(self, phase_engine):
        """Verify PhaseEngine.is_bypass_phase works correctly."""
        assert phase_engine.is_bypass_phase("troubleshoot") is True
        assert phase_engine.is_bypass_phase("explore") is False

    def test_can_bypass_to_from_coding_phase(self, phase_engine):
        """Verify can_bypass_to allows from coding phases."""
        is_valid, msg = phase_engine.can_bypass_to("write-code", "troubleshoot")
        assert is_valid is True
        assert msg == ""

    def test_can_bypass_to_blocked_from_pre_coding(self, phase_engine):
        """Verify can_bypass_to blocks from pre-coding phases."""
        is_valid, msg = phase_engine.can_bypass_to("explore", "troubleshoot")
        assert is_valid is False
        assert "pre-coding" in msg.lower()

    def test_is_valid_transition_to_troubleshoot(self, phase_engine):
        """Verify is_valid_transition allows to troubleshoot from coding phase."""
        is_valid, msg = phase_engine.is_valid_transition("write-code", "troubleshoot")
        assert is_valid is True

    def test_is_valid_transition_blocked_from_explore(self, phase_engine):
        """Verify is_valid_transition blocks troubleshoot from explore."""
        is_valid, msg = phase_engine.is_valid_transition("explore", "troubleshoot")
        assert is_valid is False


class TestStateManagerTroubleshoot:
    """Tests for StateManager troubleshoot methods."""

    def test_is_troubleshoot_active_default_false(self, state_manager):
        """Verify troubleshoot is not active by default."""
        assert state_manager.is_troubleshoot_active() is False

    def test_activate_troubleshoot(self, state_manager):
        """Verify activate_troubleshoot sets correct state."""
        state_manager.set_current_phase("write-code")
        state_manager.activate_troubleshoot()

        assert state_manager.is_troubleshoot_active() is True
        assert state_manager.get_current_phase() == "troubleshoot"
        assert state_manager.get_pre_troubleshoot_phase() == "write-code"

    def test_deactivate_troubleshoot(self, state_manager):
        """Verify deactivate_troubleshoot restores previous phase."""
        state_manager.set_current_phase("refactor")
        state_manager.activate_troubleshoot()
        state_manager.deactivate_troubleshoot()

        assert state_manager.is_troubleshoot_active() is False
        assert state_manager.get_current_phase() == "refactor"
        assert state_manager.get_pre_troubleshoot_phase() is None

    def test_get_pre_troubleshoot_phase(self, state_manager):
        """Verify get_pre_troubleshoot_phase returns stored phase."""
        state_manager.set_current_phase("validate")
        state_manager.activate_troubleshoot()

        assert state_manager.get_pre_troubleshoot_phase() == "validate"


class TestTroubleshootTrigger:
    """Tests for troubleshoot trigger detection."""

    def test_troubleshoot_trigger_detected(self):
        """Verify /troubleshoot command is detected."""
        from handlers.user_prompt import UserPromptHandler

        handler = UserPromptHandler()
        assert handler.is_troubleshoot_triggered("/troubleshoot") is True
        assert handler.is_troubleshoot_triggered("some /troubleshoot cmd") is True

    def test_troubleshoot_trigger_not_detected(self):
        """Verify non-troubleshoot prompts are not detected."""
        from handlers.user_prompt import UserPromptHandler

        handler = UserPromptHandler()
        assert handler.is_troubleshoot_triggered("/implement T001") is False
        assert handler.is_troubleshoot_triggered("help me troubleshoot") is False


class TestTroubleshootAgentMapping:
    """Tests for troubleshoot agent mapping."""

    def test_troubleshoot_owned_by_troubleshooter(self):
        """Verify troubleshoot phase is owned by troubleshooter agent."""
        from config.unified_loader import get_agent_for_phase

        agent = get_agent_for_phase("troubleshoot")
        assert agent == "troubleshooter"


class TestTroubleshootWorkflow:
    """Integration tests for troubleshoot workflow."""

    def test_full_troubleshoot_cycle(self, state_manager):
        """Test complete troubleshoot activate/deactivate cycle."""
        # Start in write-code phase
        state_manager.set_current_phase("write-code")
        state_manager.activate_workflow()

        # Activate troubleshoot
        state_manager.activate_troubleshoot()
        assert state_manager.get_current_phase() == "troubleshoot"
        assert state_manager.is_troubleshoot_active() is True

        # Deactivate troubleshoot
        state_manager.deactivate_troubleshoot()
        assert state_manager.get_current_phase() == "write-code"
        assert state_manager.is_troubleshoot_active() is False

    def test_troubleshoot_from_multiple_coding_phases(self, state_manager):
        """Test troubleshoot can be activated from various coding phases."""
        coding_phases = ["write-tests", "write-code", "refactor", "validate"]

        for phase in coding_phases:
            state_manager.set_current_phase(phase)
            state_manager.activate_troubleshoot()
            assert state_manager.get_pre_troubleshoot_phase() == phase
            state_manager.deactivate_troubleshoot()
            assert state_manager.get_current_phase() == phase


class TestPhaseTrackerTroubleshoot:
    """Tests for PhaseTracker handling of troubleshoot phase."""

    def test_phase_tracker_activates_troubleshoot(self, tmp_path):
        """Verify PhaseTracker.track() activates troubleshoot mode."""
        from trackers.phase_tracker import PhaseTracker
        from core.state_manager import StateManager

        state_path = tmp_path / "state.json"
        manager = StateManager(state_path)
        manager.reset()
        manager.activate_workflow()
        manager.set_current_phase("write-code")

        with patch("trackers.phase_tracker.get_manager", return_value=manager), patch(
            "trackers.phase_tracker.get_tracker"
        ) as mock_tracker:
            mock_deliverables = MagicMock()
            mock_tracker.return_value = mock_deliverables

            tracker = PhaseTracker()
            tracker.track("troubleshoot")

            assert manager.is_troubleshoot_active() is True
            assert manager.get_current_phase() == "troubleshoot"
            assert manager.get_pre_troubleshoot_phase() == "write-code"

    def test_phase_tracker_toggles_troubleshoot_off(self, tmp_path):
        """Verify PhaseTracker.track() toggles troubleshoot off when called again."""
        from trackers.phase_tracker import PhaseTracker
        from core.state_manager import StateManager

        state_path = tmp_path / "state.json"
        manager = StateManager(state_path)
        manager.reset()
        manager.activate_workflow()
        manager.set_current_phase("write-code")
        manager.activate_troubleshoot()

        with patch("trackers.phase_tracker.get_manager", return_value=manager), patch(
            "trackers.phase_tracker.get_tracker"
        ) as mock_tracker:
            mock_deliverables = MagicMock()
            mock_tracker.return_value = mock_deliverables

            tracker = PhaseTracker()
            tracker.track("troubleshoot")

            assert manager.is_troubleshoot_active() is False
            assert manager.get_current_phase() == "write-code"

    def test_phase_tracker_exits_troubleshoot_on_regular_phase(self, tmp_path):
        """Verify PhaseTracker exits troubleshoot when tracking regular phase."""
        from trackers.phase_tracker import PhaseTracker
        from core.state_manager import StateManager

        state_path = tmp_path / "state.json"
        manager = StateManager(state_path)
        manager.reset()
        manager.activate_workflow()
        manager.set_current_phase("write-code")
        manager.activate_troubleshoot()

        with patch("trackers.phase_tracker.get_manager", return_value=manager), patch(
            "trackers.phase_tracker.get_tracker"
        ) as mock_tracker:
            mock_deliverables = MagicMock()
            mock_tracker.return_value = mock_deliverables

            tracker = PhaseTracker()
            tracker.track("refactor")

            assert manager.is_troubleshoot_active() is False
            assert manager.get_current_phase() == "refactor"

    def test_phase_tracker_run_with_troubleshoot_skill(self, tmp_path):
        """Verify PhaseTracker.run() handles troubleshoot skill correctly."""
        from trackers.phase_tracker import PhaseTracker
        from core.state_manager import StateManager

        state_path = tmp_path / "state.json"
        manager = StateManager(state_path)
        manager.reset()
        manager.activate_workflow()
        manager.set_current_phase("write-code")

        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "workflow:troubleshoot"},
        }

        with patch("trackers.phase_tracker.get_manager", return_value=manager), patch(
            "trackers.phase_tracker.get_tracker"
        ) as mock_tracker:
            mock_deliverables = MagicMock()
            mock_tracker.return_value = mock_deliverables

            tracker = PhaseTracker()
            tracker.run(hook_input)

            assert manager.is_troubleshoot_active() is True
            assert manager.get_current_phase() == "troubleshoot"
