#!/usr/bin/env python3
"""Pytest tests for the deliverables_exit guard module."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from guards.deliverables_exit import (  # type: ignore
    DeliverablesExitGuard,
    validate_deliverables_exit,
)


@pytest.fixture
def guard():
    """Provide a guard instance with mocked dependencies."""
    with patch("guards.deliverables_exit.get_manager") as mock_manager, patch(
        "guards.deliverables_exit.get_tracker"
    ) as mock_tracker:
        mock_manager.return_value.is_workflow_active.return_value = True
        mock_tracker.return_value.are_all_met.return_value = (True, "All met")
        mock_tracker.return_value.get_deliverables.return_value = []
        mock_tracker.return_value.get_complete.return_value = []
        yield DeliverablesExitGuard()


@pytest.fixture
def inactive_guard():
    """Provide a guard instance with inactive workflow."""
    with patch("guards.deliverables_exit.get_manager") as mock_manager, patch(
        "guards.deliverables_exit.get_tracker"
    ) as mock_tracker:
        mock_manager.return_value.is_workflow_active.return_value = False
        yield DeliverablesExitGuard()


class TestIsActive:
    """Tests for is_active method."""

    def test_active_when_workflow_active(self, guard):
        """Returns True when workflow is active."""
        assert guard.is_active() is True

    def test_inactive_when_workflow_inactive(self, inactive_guard):
        """Returns False when workflow is inactive."""
        assert inactive_guard.is_active() is False


class TestValidateDeliverables:
    """Tests for validate_deliverables method."""

    def test_validate_deliverables_returns_unmet_message(self):
        """Check returns (False, msg) when incomplete."""
        with patch("guards.deliverables_exit.get_manager") as mock_manager, patch(
            "guards.deliverables_exit.get_tracker"
        ) as mock_tracker:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_tracker.return_value.are_all_met.return_value = (
                False,
                "Deliverable not met: write codebase-status_*.md",
            )

            guard = DeliverablesExitGuard()
            is_met, message = guard.validate_deliverables()

            assert is_met is False
            assert "not met" in message.lower()

    def test_validate_deliverables_returns_true_when_all_met(self):
        """Check returns (True, msg) when all deliverables met."""
        with patch("guards.deliverables_exit.get_manager") as mock_manager, patch(
            "guards.deliverables_exit.get_tracker"
        ) as mock_tracker:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_tracker.return_value.are_all_met.return_value = (
                True,
                "All deliverables met",
            )

            guard = DeliverablesExitGuard()
            is_met, message = guard.validate_deliverables()

            assert is_met is True


class TestValidateScs:
    """Tests for validate_scs method."""

    def test_validate_scs_returns_true_when_import_fails(self):
        """SC validation unavailable returns True (allow)."""
        with patch("guards.deliverables_exit.get_manager") as mock_manager, patch(
            "guards.deliverables_exit.get_tracker"
        ) as mock_tracker, patch.dict(sys.modules, {"roadmap.utils": None}):
            mock_manager.return_value.is_workflow_active.return_value = True

            guard = DeliverablesExitGuard()
            # Should return True when import fails
            is_met, _ = guard.validate_scs()

            assert is_met is True


class TestRun:
    """Tests for run method."""

    def test_run_blocks_when_deliverables_not_met(self, capsys):
        """Verify exit 2 and JSON output when incomplete."""
        with patch("guards.deliverables_exit.get_manager") as mock_manager, patch(
            "guards.deliverables_exit.get_tracker"
        ) as mock_tracker, patch("core.workflow_auditor.get_auditor") as mock_auditor:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_tracker.return_value.are_all_met.return_value = (
                False,
                "Missing deliverable: read codebase.md",
            )
            mock_auditor.return_value = MagicMock()

            guard = DeliverablesExitGuard()

            with pytest.raises(SystemExit) as exc_info:
                guard.run({"hook_event_name": "SubagentStop"})

            assert exc_info.value.code == 2

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output["decision"] == "block"
            assert "Missing deliverable" in output["reason"]

    def test_run_allows_when_all_met(self):
        """Verify exit 0 when all deliverables met."""
        with patch("guards.deliverables_exit.get_manager") as mock_manager, patch(
            "guards.deliverables_exit.get_tracker"
        ) as mock_tracker, patch("core.workflow_auditor.get_auditor") as mock_auditor:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_tracker.return_value.are_all_met.return_value = (True, "All met")
            mock_tracker.return_value.get_deliverables.return_value = [
                {"type": "files", "completed": True}
            ]
            mock_tracker.return_value.get_complete.return_value = [
                {"type": "files", "completed": True}
            ]
            mock_auditor.return_value = MagicMock()

            guard = DeliverablesExitGuard()

            # Need to also mock validate_scs
            with patch.object(
                guard, "validate_scs", return_value=(True, "All SCs met")
            ):
                with pytest.raises(SystemExit) as exc_info:
                    guard.run({"hook_event_name": "SubagentStop"})

                assert exc_info.value.code == 0

    def test_run_exits_early_when_inactive(self, inactive_guard):
        """Verify exit 0 when workflow inactive."""
        with pytest.raises(SystemExit) as exc_info:
            inactive_guard.run({"hook_event_name": "SubagentStop"})
        assert exc_info.value.code == 0

    def test_run_blocks_when_scs_not_met(self, capsys):
        """Verify exit 2 when SCs not met."""
        with patch("guards.deliverables_exit.get_manager") as mock_manager, patch(
            "guards.deliverables_exit.get_tracker"
        ) as mock_tracker, patch("core.workflow_auditor.get_auditor") as mock_auditor:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_tracker.return_value.are_all_met.return_value = (True, "All met")
            mock_tracker.return_value.get_deliverables.return_value = []
            mock_tracker.return_value.get_complete.return_value = []
            mock_auditor.return_value = MagicMock()

            guard = DeliverablesExitGuard()

            with patch.object(
                guard, "validate_scs", return_value=(False, "SC-001 not met")
            ):
                with pytest.raises(SystemExit) as exc_info:
                    guard.run({"hook_event_name": "SubagentStop"})

                assert exc_info.value.code == 2

                captured = capsys.readouterr()
                output = json.loads(captured.out)
                assert output["decision"] == "block"
                assert "SC-001" in output["reason"]


class TestValidateDeliverablesExitFunction:
    """Tests for validate_deliverables_exit convenience function."""

    def test_validate_deliverables_exit_returns_false_when_deliverables_not_met(self):
        """validate_deliverables_exit returns False when deliverables not met."""
        with patch("guards.deliverables_exit.get_manager") as mock_manager, patch(
            "guards.deliverables_exit.get_tracker"
        ) as mock_tracker:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_tracker.return_value.are_all_met.return_value = (
                False,
                "Missing: codebase.md",
            )

            is_met, message = validate_deliverables_exit()

            assert is_met is False
            assert "Missing" in message

    def test_validate_deliverables_exit_returns_true_when_all_met(self):
        """validate_deliverables_exit returns True when all met."""
        with patch("guards.deliverables_exit.get_manager") as mock_manager, patch(
            "guards.deliverables_exit.get_tracker"
        ) as mock_tracker:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_tracker.return_value.are_all_met.return_value = (True, "All met")

            guard = DeliverablesExitGuard()
            with patch.object(
                guard, "validate_scs", return_value=(True, "All SCs met")
            ):
                # The function creates its own guard, so we patch at module level
                with patch(
                    "guards.deliverables_exit.DeliverablesExitGuard"
                ) as MockGuard:
                    mock_guard_instance = MagicMock()
                    mock_guard_instance.validate_deliverables.return_value = (
                        True,
                        "All met",
                    )
                    mock_guard_instance.validate_scs.return_value = (
                        True,
                        "All SCs met",
                    )
                    MockGuard.return_value = mock_guard_instance

                    is_met, message = validate_deliverables_exit()

                    assert is_met is True


class TestImports:
    """Tests for module imports."""

    def test_guard_import(self):
        """DeliverablesExitGuard can be imported."""
        from guards.deliverables_exit import DeliverablesExitGuard

        assert DeliverablesExitGuard is not None

    def test_function_import(self):
        """validate_deliverables_exit function can be imported."""
        from guards.deliverables_exit import validate_deliverables_exit

        assert callable(validate_deliverables_exit)

    def test_main_import(self):
        """main function can be imported."""
        from guards.deliverables_exit import main

        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
