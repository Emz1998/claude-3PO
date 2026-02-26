#!/usr/bin/env python3
"""Pytest tests for the subagent_stop handler module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handlers.subagent_stop import (  # type: ignore
    SubagentStopHandler,
    handle_subagent_stop,
)


@pytest.fixture
def handler():
    """Provide a handler instance with mocked dependencies."""
    with patch("handlers.subagent_stop.get_manager") as mock_manager, patch(
        "handlers.subagent_stop.DeliverablesExitGuard"
    ) as mock_guard:
        mock_manager.return_value.is_workflow_active.return_value = True
        mock_guard_instance = MagicMock()
        mock_guard.return_value = mock_guard_instance
        yield SubagentStopHandler()


@pytest.fixture
def inactive_handler():
    """Provide a handler instance with inactive workflow."""
    with patch("handlers.subagent_stop.get_manager") as mock_manager, patch(
        "handlers.subagent_stop.DeliverablesExitGuard"
    ) as mock_guard:
        mock_manager.return_value.is_workflow_active.return_value = False
        yield SubagentStopHandler()


class TestIsActive:
    """Tests for is_active method."""

    def test_active_when_workflow_active(self, handler):
        """Returns True when workflow is active."""
        assert handler.is_active() is True

    def test_inactive_when_workflow_inactive(self, inactive_handler):
        """Returns False when workflow is inactive."""
        assert inactive_handler.is_active() is False


class TestRun:
    """Tests for run method."""

    def test_run_delegates_to_exit_guard(self):
        """Verify calls DeliverablesExitGuard.run()."""
        with patch("handlers.subagent_stop.get_manager") as mock_manager, patch(
            "handlers.subagent_stop.DeliverablesExitGuard"
        ) as mock_guard:
            mock_manager.return_value.is_workflow_active.return_value = True

            mock_guard_instance = MagicMock()
            mock_guard.return_value = mock_guard_instance

            handler = SubagentStopHandler()
            hook_input = {
                "hook_event_name": "SubagentStop",
                "stop_hook_active": False,
                "agent_id": "ae60f8a",
                "agent_transcript_path": "/path/to/transcript",
            }
            handler.run(hook_input)

            mock_guard_instance.run.assert_called_once_with(hook_input)

    def test_run_exits_early_when_inactive(self, inactive_handler):
        """Verify exits when workflow inactive."""
        hook_input = {
            "hook_event_name": "SubagentStop",
            "stop_hook_active": False,
            "agent_id": "ae60f8a",
        }
        with pytest.raises(SystemExit) as exc_info:
            inactive_handler.run(hook_input)
        assert exc_info.value.code == 0

    def test_run_ignores_non_subagent_stop_events(self):
        """Verify ignores other events."""
        with patch("handlers.subagent_stop.get_manager") as mock_manager, patch(
            "handlers.subagent_stop.DeliverablesExitGuard"
        ) as mock_guard:
            mock_manager.return_value.is_workflow_active.return_value = True

            mock_guard_instance = MagicMock()
            mock_guard.return_value = mock_guard_instance

            handler = SubagentStopHandler()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "explore"},
            }

            with pytest.raises(SystemExit) as exc_info:
                handler.run(hook_input)
            assert exc_info.value.code == 0

            # Should not call exit guard
            mock_guard_instance.run.assert_not_called()

    def test_run_handles_stop_hook_active_flag(self):
        """Verify handles stop_hook_active flag in input."""
        with patch("handlers.subagent_stop.get_manager") as mock_manager, patch(
            "handlers.subagent_stop.DeliverablesExitGuard"
        ) as mock_guard:
            mock_manager.return_value.is_workflow_active.return_value = True

            mock_guard_instance = MagicMock()
            mock_guard.return_value = mock_guard_instance

            handler = SubagentStopHandler()
            hook_input = {
                "hook_event_name": "SubagentStop",
                "stop_hook_active": True,
                "agent_id": "ae60f8a",
            }
            handler.run(hook_input)

            # Should still delegate to exit guard
            mock_guard_instance.run.assert_called_once_with(hook_input)


class TestHandleSubagentStopFunction:
    """Tests for handle_subagent_stop convenience function."""

    def test_handle_subagent_stop_works(self):
        """Verify handle_subagent_stop function works correctly."""
        with patch("handlers.subagent_stop.get_manager") as mock_manager, patch(
            "handlers.subagent_stop.DeliverablesExitGuard"
        ) as mock_guard:
            mock_manager.return_value.is_workflow_active.return_value = False

            hook_input = {
                "hook_event_name": "SubagentStop",
                "agent_id": "ae60f8a",
            }

            with pytest.raises(SystemExit) as exc_info:
                handle_subagent_stop(hook_input)
            assert exc_info.value.code == 0


class TestImports:
    """Tests for module imports."""

    def test_handler_import(self):
        """SubagentStopHandler can be imported."""
        from handlers.subagent_stop import SubagentStopHandler

        assert SubagentStopHandler is not None

    def test_function_import(self):
        """handle_subagent_stop function can be imported."""
        from handlers.subagent_stop import handle_subagent_stop

        assert callable(handle_subagent_stop)

    def test_main_import(self):
        """main function can be imported."""
        from handlers.subagent_stop import main

        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
