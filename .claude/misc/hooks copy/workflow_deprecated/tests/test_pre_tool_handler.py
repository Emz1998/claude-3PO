#!/usr/bin/env python3
"""Pytest tests for the pre_tool handler module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handlers.pre_tool import (  # type: ignore
    PreToolHandler,
    handle_pre_tool,
    _map_tool_to_action,
    _get_tool_value,
)


@pytest.fixture
def handler():
    """Provide a handler instance with mocked dependencies."""
    with patch("handlers.pre_tool.get_manager") as mock_manager, patch(
        "handlers.pre_tool.PhaseTransitionGuard"
    ) as mock_phase_guard, patch(
        "handlers.pre_tool.SubagentAccessGuard"
    ) as mock_subagent_guard, patch(
        "handlers.pre_tool.ReleasePlanTracker"
    ) as mock_tracker, patch(
        "handlers.pre_tool.get_current_feature_id"
    ) as mock_feature_id, patch(
        "handlers.pre_tool.get_feature_test_strategy"
    ) as mock_strategy:
        mock_manager.return_value.is_workflow_active.return_value = True
        mock_manager.return_value.get_strict_order_block_reason.return_value = None
        mock_feature_id.return_value = "FEAT-001"
        mock_strategy.return_value = "TDD"
        yield PreToolHandler()


@pytest.fixture
def inactive_handler():
    """Provide a handler instance with inactive workflow."""
    with patch("handlers.pre_tool.get_manager") as mock_manager, patch(
        "handlers.pre_tool.PhaseTransitionGuard"
    ) as mock_phase_guard, patch(
        "handlers.pre_tool.SubagentAccessGuard"
    ) as mock_subagent_guard, patch(
        "handlers.pre_tool.ReleasePlanTracker"
    ) as mock_tracker, patch(
        "handlers.pre_tool.get_current_feature_id"
    ) as mock_feature_id, patch(
        "handlers.pre_tool.get_feature_test_strategy"
    ) as mock_strategy:
        mock_manager.return_value.is_workflow_active.return_value = False
        mock_feature_id.return_value = None
        mock_strategy.return_value = None
        yield PreToolHandler()


class TestIsActive:
    """Tests for is_active method."""

    def test_active_when_workflow_active(self, handler):
        """Returns True when workflow is active."""
        assert handler.is_active() is True

    def test_inactive_when_workflow_inactive(self, inactive_handler):
        """Returns False when workflow is inactive."""
        assert inactive_handler.is_active() is False


class TestMapToolToAction:
    """Tests for _map_tool_to_action helper function."""

    def test_map_read_tool(self):
        """Maps Read to read action."""
        assert _map_tool_to_action("Read") == "read"

    def test_map_write_tool(self):
        """Maps Write to write action."""
        assert _map_tool_to_action("Write") == "write"

    def test_map_edit_tool(self):
        """Maps Edit to edit action."""
        assert _map_tool_to_action("Edit") == "edit"

    def test_map_bash_tool(self):
        """Maps Bash to bash action."""
        assert _map_tool_to_action("Bash") == "bash"

    def test_map_skill_tool(self):
        """Maps Skill to invoke action."""
        assert _map_tool_to_action("Skill") == "invoke"

    def test_map_unknown_tool(self):
        """Returns None for unknown tools."""
        assert _map_tool_to_action("Task") is None
        assert _map_tool_to_action("Unknown") is None


class TestGetToolValue:
    """Tests for _get_tool_value helper function."""

    def test_get_file_path_for_read(self):
        """Extracts file_path for Read tool."""
        result = _get_tool_value("Read", {"file_path": "/some/file.ts"})
        assert result == "/some/file.ts"

    def test_get_file_path_for_write(self):
        """Extracts file_path for Write tool."""
        result = _get_tool_value("Write", {"file_path": "/some/file.ts"})
        assert result == "/some/file.ts"

    def test_get_file_path_for_edit(self):
        """Extracts file_path for Edit tool."""
        result = _get_tool_value("Edit", {"file_path": "/some/file.ts"})
        assert result == "/some/file.ts"

    def test_get_command_for_bash(self):
        """Extracts command for Bash tool."""
        result = _get_tool_value("Bash", {"command": "npm test"})
        assert result == "npm test"

    def test_get_skill_for_skill(self):
        """Extracts skill for Skill tool."""
        result = _get_tool_value("Skill", {"skill": "explore"})
        assert result == "explore"

    def test_returns_empty_for_unknown(self):
        """Returns empty string for unknown tools."""
        result = _get_tool_value("Task", {"subagent_type": "Explore"})
        assert result == ""


class TestCheckStrictOrder:
    """Tests for check_strict_order method."""

    def test_check_strict_order_allows_when_no_block(self):
        """Allows tool when no strict order block."""
        with patch("handlers.pre_tool.get_manager") as mock_manager, patch(
            "handlers.pre_tool.PhaseTransitionGuard"
        ), patch("handlers.pre_tool.SubagentAccessGuard"), patch(
            "handlers.pre_tool.ReleasePlanTracker"
        ), patch(
            "handlers.pre_tool.get_current_feature_id"
        ) as mock_feature_id, patch(
            "handlers.pre_tool.get_feature_test_strategy"
        ) as mock_strategy:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_strict_order_block_reason.return_value = None
            mock_feature_id.return_value = "FEAT-001"
            mock_strategy.return_value = "TDD"

            handler = PreToolHandler()
            # Should not raise
            handler.check_strict_order("Read", {"file_path": "/some/file.ts"})

    def test_check_strict_order_blocks_when_reason_provided(self):
        """Blocks tool when strict order block reason exists."""
        with patch("handlers.pre_tool.get_manager") as mock_manager, patch(
            "handlers.pre_tool.PhaseTransitionGuard"
        ), patch("handlers.pre_tool.SubagentAccessGuard"), patch(
            "handlers.pre_tool.ReleasePlanTracker"
        ), patch(
            "handlers.pre_tool.get_current_feature_id"
        ) as mock_feature_id, patch(
            "handlers.pre_tool.get_feature_test_strategy"
        ) as mock_strategy, patch(
            "core.workflow_auditor.get_auditor"
        ) as mock_auditor:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_strict_order_block_reason.return_value = (
                "Must read config.ts before helpers.ts"
            )
            mock_feature_id.return_value = "FEAT-001"
            mock_strategy.return_value = "TDD"
            mock_auditor.return_value = MagicMock()

            handler = PreToolHandler()

            with pytest.raises(SystemExit) as exc_info:
                handler.check_strict_order("Read", {"file_path": "/some/helpers.ts"})
            assert exc_info.value.code == 2


class TestRun:
    """Tests for run method."""

    def test_run_routes_skill_to_phase_guard(self):
        """Verify Skill → phase transition guard."""
        with patch("handlers.pre_tool.get_manager") as mock_manager, patch(
            "handlers.pre_tool.PhaseTransitionGuard"
        ) as mock_phase_guard, patch("handlers.pre_tool.SubagentAccessGuard"), patch(
            "handlers.pre_tool.ReleasePlanTracker"
        ) as mock_tracker, patch(
            "handlers.pre_tool.get_current_feature_id"
        ) as mock_feature_id, patch(
            "handlers.pre_tool.get_feature_test_strategy"
        ) as mock_strategy:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_strict_order_block_reason.return_value = None
            mock_feature_id.return_value = "FEAT-001"
            mock_strategy.return_value = "TDD"

            mock_guard_instance = MagicMock()
            mock_phase_guard.return_value = mock_guard_instance

            handler = PreToolHandler()
            hook_input = {
                "hook_event_name": "PreToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "plan"},
            }

            with pytest.raises(SystemExit) as exc_info:
                handler.run(hook_input)

            # Should call phase guard run
            mock_guard_instance.run.assert_called_once_with(hook_input)

    def test_run_routes_task_to_subagent_guard(self):
        """Verify Task → subagent access guard."""
        with patch("handlers.pre_tool.get_manager") as mock_manager, patch(
            "handlers.pre_tool.PhaseTransitionGuard"
        ), patch("handlers.pre_tool.SubagentAccessGuard") as mock_subagent_guard, patch(
            "handlers.pre_tool.ReleasePlanTracker"
        ), patch(
            "handlers.pre_tool.get_current_feature_id"
        ) as mock_feature_id, patch(
            "handlers.pre_tool.get_feature_test_strategy"
        ) as mock_strategy:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_manager.return_value.get_strict_order_block_reason.return_value = None
            mock_feature_id.return_value = "FEAT-001"
            mock_strategy.return_value = "TDD"

            mock_guard_instance = MagicMock()
            mock_subagent_guard.return_value = mock_guard_instance

            handler = PreToolHandler()
            hook_input = {
                "hook_event_name": "PreToolUse",
                "tool_name": "Task",
                "tool_input": {"subagent_type": "Explore"},
            }

            with pytest.raises(SystemExit) as exc_info:
                handler.run(hook_input)

            # Should call subagent guard run
            mock_guard_instance.run.assert_called_once_with(hook_input)

    def test_run_checks_strict_order_for_read_write_edit(self):
        """Verify strict order check for Read/Write/Edit."""
        with patch("handlers.pre_tool.get_manager") as mock_manager, patch(
            "handlers.pre_tool.PhaseTransitionGuard"
        ), patch("handlers.pre_tool.SubagentAccessGuard"), patch(
            "handlers.pre_tool.ReleasePlanTracker"
        ), patch(
            "handlers.pre_tool.get_current_feature_id"
        ) as mock_feature_id, patch(
            "handlers.pre_tool.get_feature_test_strategy"
        ) as mock_strategy:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_feature_id.return_value = "FEAT-001"
            mock_strategy.return_value = "TDD"

            handler = PreToolHandler()
            hook_input = {
                "hook_event_name": "PreToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "/some/file.ts"},
            }

            # Should call get_strict_order_block_reason
            mock_manager.return_value.get_strict_order_block_reason.return_value = None

            with pytest.raises(SystemExit) as exc_info:
                handler.run(hook_input)

            mock_manager.return_value.get_strict_order_block_reason.assert_called_once()

    def test_run_exits_early_when_inactive(self, inactive_handler):
        """Verify exits when workflow inactive."""
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "explore"},
        }
        with pytest.raises(SystemExit) as exc_info:
            inactive_handler.run(hook_input)
        assert exc_info.value.code == 0

    def test_run_ignores_non_pre_tool_use_events(self):
        """Verify ignores other events."""
        with patch("handlers.pre_tool.get_manager") as mock_manager, patch(
            "handlers.pre_tool.PhaseTransitionGuard"
        ), patch("handlers.pre_tool.SubagentAccessGuard"), patch(
            "handlers.pre_tool.ReleasePlanTracker"
        ), patch(
            "handlers.pre_tool.get_current_feature_id"
        ) as mock_feature_id, patch(
            "handlers.pre_tool.get_feature_test_strategy"
        ) as mock_strategy:
            mock_manager.return_value.is_workflow_active.return_value = True
            mock_feature_id.return_value = "FEAT-001"
            mock_strategy.return_value = "TDD"

            handler = PreToolHandler()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "explore"},
            }

            with pytest.raises(SystemExit) as exc_info:
                handler.run(hook_input)
            assert exc_info.value.code == 0


class TestHandlePreToolFunction:
    """Tests for handle_pre_tool convenience function."""

    def test_handle_pre_tool_works(self):
        """Verify handle_pre_tool function works correctly."""
        with patch("handlers.pre_tool.get_manager") as mock_manager, patch(
            "handlers.pre_tool.PhaseTransitionGuard"
        ), patch("handlers.pre_tool.SubagentAccessGuard"), patch(
            "handlers.pre_tool.ReleasePlanTracker"
        ), patch(
            "handlers.pre_tool.get_current_feature_id"
        ) as mock_feature_id, patch(
            "handlers.pre_tool.get_feature_test_strategy"
        ) as mock_strategy:
            mock_manager.return_value.is_workflow_active.return_value = False
            mock_feature_id.return_value = None
            mock_strategy.return_value = None

            hook_input = {
                "hook_event_name": "PreToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "/some/file.ts"},
            }

            with pytest.raises(SystemExit) as exc_info:
                handle_pre_tool(hook_input)
            assert exc_info.value.code == 0


class TestImports:
    """Tests for module imports."""

    def test_handler_import(self):
        """PreToolHandler can be imported."""
        from handlers.pre_tool import PreToolHandler

        assert PreToolHandler is not None

    def test_function_import(self):
        """handle_pre_tool function can be imported."""
        from handlers.pre_tool import handle_pre_tool

        assert callable(handle_pre_tool)

    def test_helper_imports(self):
        """Helper functions can be imported."""
        from handlers.pre_tool import _map_tool_to_action, _get_tool_value

        assert callable(_map_tool_to_action)
        assert callable(_get_tool_value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
