#!/usr/bin/env python3
"""Pytest tests for the context_injector module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from context.context_injector import (  # type: ignore
    ContextInjector,
    inject_phase_context,
)


@pytest.fixture
def injector():
    """Provide an injector instance with mocked dependencies."""
    with patch("context.context_injector.get_manager") as mock_manager:
        mock_manager.return_value.is_workflow_active.return_value = True
        mock_manager.return_value.get_pending_validation.return_value = None
        yield ContextInjector()


@pytest.fixture
def inactive_injector():
    """Provide an injector instance with inactive workflow."""
    with patch("context.context_injector.get_manager") as mock_manager:
        mock_manager.return_value.is_workflow_active.return_value = False
        yield ContextInjector()


class TestIsActive:
    """Tests for is_active method."""

    def test_active_when_workflow_active(self, injector):
        """Returns True when workflow is active."""
        assert injector.is_active() is True

    def test_inactive_when_workflow_inactive(self, inactive_injector):
        """Returns False when workflow is inactive."""
        assert inactive_injector.is_active() is False


class TestInject:
    """Tests for inject method."""

    def test_inject_calls_get_phase_reminder(self):
        """Verify inject() calls get_phase_reminder."""
        with patch("context.context_injector.get_manager") as mock_manager, \
             patch("context.context_injector.get_phase_reminder") as mock_reminder, \
             patch("context.context_injector.add_context") as mock_add_context:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_pending_validation.return_value = None
            mock_reminder.return_value = "## Phase: EXPLORE\nExplore the codebase."

            injector = ContextInjector()
            result = injector.inject("explore")

            mock_reminder.assert_called_once_with("explore")
            mock_add_context.assert_called_once()
            assert result is True

    def test_inject_returns_false_when_no_reminder(self):
        """Verify returns False when no reminder available."""
        with patch("context.context_injector.get_manager") as mock_manager, \
             patch("context.context_injector.get_phase_reminder") as mock_reminder:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_pending_validation.return_value = None
            mock_reminder.return_value = None

            injector = ContextInjector()
            result = injector.inject("unknown-phase")

            assert result is False


class TestInjectValidationContext:
    """Tests for inject_validation_context method."""

    def test_inject_validation_context_when_pending(self):
        """Verify validation context injection when pending_validation is set."""
        with patch("context.context_injector.get_manager") as mock_manager, \
             patch("context.context_injector.add_context") as mock_add_context:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_pending_validation.return_value = "ac"

            # Mock the criteria_validator import
            with patch.dict(sys.modules, {"validators.criteria_validator": MagicMock()}):
                sys.modules["validators.criteria_validator"].get_unmet_acs = MagicMock(
                    return_value=["AC-001", "AC-002"]
                )
                sys.modules["validators.criteria_validator"].get_unmet_scs = MagicMock()
                sys.modules["validators.criteria_validator"].get_unmet_epic_scs = MagicMock()

                injector = ContextInjector()
                result = injector.inject_validation_context()

                assert result is True
                mock_add_context.assert_called_once()
                # Check the context contains validation info
                call_args = mock_add_context.call_args[0][0]
                assert "VALIDATION REQUIRED" in call_args

    def test_inject_validation_context_returns_false_when_no_pending(self):
        """Verify returns False when no pending_validation."""
        with patch("context.context_injector.get_manager") as mock_manager:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_pending_validation.return_value = None

            injector = ContextInjector()
            result = injector.inject_validation_context()

            assert result is False


class TestRun:
    """Tests for run method."""

    def test_run_injects_for_skill_tool(self):
        """Verify run() processes Skill tool correctly."""
        with patch("context.context_injector.get_manager") as mock_manager, \
             patch("context.context_injector.get_phase_reminder") as mock_reminder, \
             patch("context.context_injector.add_context") as mock_add_context, \
             patch("context.context_injector.normalize_skill_name") as mock_normalize:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_pending_validation.return_value = None
            mock_reminder.return_value = "## Phase: PLAN\nCreate plan."
            mock_normalize.return_value = "plan"

            injector = ContextInjector()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "plan"},
            }
            injector.run(hook_input)

            mock_reminder.assert_called_once_with("plan")
            mock_add_context.assert_called_once()

    def test_run_normalizes_workflow_prefix(self):
        """Verify workflow:explore → explore normalization."""
        with patch("context.context_injector.get_manager") as mock_manager, \
             patch("context.context_injector.get_phase_reminder") as mock_reminder, \
             patch("context.context_injector.add_context") as mock_add_context, \
             patch("context.context_injector.normalize_skill_name") as mock_normalize:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_pending_validation.return_value = None
            mock_reminder.return_value = "## Phase: EXPLORE"
            mock_normalize.return_value = "explore"

            injector = ContextInjector()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "workflow:explore"},
            }
            injector.run(hook_input)

            mock_normalize.assert_called_with("workflow:explore")

    def test_run_exits_early_when_inactive(self, inactive_injector):
        """Verify exits when workflow inactive."""
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "explore"},
        }
        with pytest.raises(SystemExit) as exc_info:
            inactive_injector.run(hook_input)
        assert exc_info.value.code == 0

    def test_run_exits_for_non_post_tool_use(self):
        """Verify exits for non-PostToolUse events."""
        with patch("context.context_injector.get_manager") as mock_manager:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_pending_validation.return_value = None

            injector = ContextInjector()
            hook_input = {
                "hook_event_name": "PreToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "explore"},
            }
            with pytest.raises(SystemExit) as exc_info:
                injector.run(hook_input)
            assert exc_info.value.code == 0

    def test_run_exits_for_non_skill_tools(self):
        """Verify exits for non-Skill tools."""
        with patch("context.context_injector.get_manager") as mock_manager:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_pending_validation.return_value = None

            injector = ContextInjector()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "/some/file.txt"},
            }
            with pytest.raises(SystemExit) as exc_info:
                injector.run(hook_input)
            assert exc_info.value.code == 0

    def test_run_exits_for_empty_skill_name(self):
        """Verify exits for empty skill name."""
        with patch("context.context_injector.get_manager") as mock_manager:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_pending_validation.return_value = None

            injector = ContextInjector()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": ""},
            }
            with pytest.raises(SystemExit) as exc_info:
                injector.run(hook_input)
            assert exc_info.value.code == 0

    def test_run_handles_validation_context_first(self):
        """Verify validation context is checked first."""
        with patch("context.context_injector.get_manager") as mock_manager, \
             patch("context.context_injector.add_context") as mock_add_context:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_pending_validation.return_value = "sc"

            with patch.dict(sys.modules, {"validators.criteria_validator": MagicMock()}):
                sys.modules["validators.criteria_validator"].get_unmet_acs = MagicMock()
                sys.modules["validators.criteria_validator"].get_unmet_scs = MagicMock(
                    return_value=["SC-001"]
                )
                sys.modules["validators.criteria_validator"].get_unmet_epic_scs = MagicMock()

                injector = ContextInjector()
                hook_input = {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Skill",
                    "tool_input": {"skill": "plan"},
                }
                # Should return early after injecting validation context
                injector.run(hook_input)

                mock_add_context.assert_called_once()
                call_args = mock_add_context.call_args[0][0]
                assert "VALIDATION REQUIRED" in call_args


class TestInjectPhaseContextFunction:
    """Tests for inject_phase_context convenience function."""

    def test_inject_phase_context_works(self):
        """Verify inject_phase_context function works correctly."""
        with patch("context.context_injector.get_manager") as mock_manager, \
             patch("context.context_injector.get_phase_reminder") as mock_reminder, \
             patch("context.context_injector.add_context") as mock_add_context:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_pending_validation.return_value = None
            mock_reminder.return_value = "## Phase: COMMIT"

            result = inject_phase_context("commit")

            assert result is True
            mock_add_context.assert_called_once()


class TestImports:
    """Tests for module imports."""

    def test_injector_import(self):
        """ContextInjector can be imported."""
        from context.context_injector import ContextInjector
        assert ContextInjector is not None

    def test_function_import(self):
        """inject_phase_context function can be imported."""
        from context.context_injector import inject_phase_context
        assert callable(inject_phase_context)

    def test_main_import(self):
        """main function can be imported."""
        from context.context_injector import main
        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
