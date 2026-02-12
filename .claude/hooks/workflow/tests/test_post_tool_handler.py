#!/usr/bin/env python3
"""Pytest tests for the post_tool handler module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handlers.post_tool import PostToolHandler, handle_post_tool  # type: ignore


@pytest.fixture
def handler():
    """Provide a handler instance with mocked dependencies."""
    with patch("handlers.post_tool.get_manager") as mock_manager, \
         patch("handlers.post_tool.PhaseTracker") as mock_phase, \
         patch("handlers.post_tool.DeliverableTracker") as mock_deliverable, \
         patch("handlers.post_tool.ReleasePlanTracker") as mock_release, \
         patch("handlers.post_tool.ContextInjector") as mock_context:
        mock_manager.return_value.is_workflow_active.return_value = True
        yield PostToolHandler()


@pytest.fixture
def inactive_handler():
    """Provide a handler instance with inactive workflow."""
    with patch("handlers.post_tool.get_manager") as mock_manager, \
         patch("handlers.post_tool.PhaseTracker"), \
         patch("handlers.post_tool.DeliverableTracker"), \
         patch("handlers.post_tool.ReleasePlanTracker"), \
         patch("handlers.post_tool.ContextInjector"):
        mock_manager.return_value.is_workflow_active.return_value = False
        yield PostToolHandler()


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

    def test_run_routes_skill_to_phase_tracker(self):
        """Verify Skill → phase tracker."""
        with patch("handlers.post_tool.get_manager") as mock_manager, \
             patch("handlers.post_tool.PhaseTracker") as mock_phase, \
             patch("handlers.post_tool.DeliverableTracker") as mock_deliverable, \
             patch("handlers.post_tool.ReleasePlanTracker") as mock_release, \
             patch("handlers.post_tool.ContextInjector") as mock_context:
            mock_manager.return_value.is_workflow_active.return_value = True

            mock_phase_instance = MagicMock()
            mock_phase.return_value = mock_phase_instance

            handler = PostToolHandler()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "explore"},
            }
            handler.run(hook_input)

            mock_phase_instance.run.assert_called_once_with(hook_input)

    def test_run_routes_skill_to_context_injector(self):
        """Verify Skill → context injector."""
        with patch("handlers.post_tool.get_manager") as mock_manager, \
             patch("handlers.post_tool.PhaseTracker") as mock_phase, \
             patch("handlers.post_tool.DeliverableTracker") as mock_deliverable, \
             patch("handlers.post_tool.ReleasePlanTracker") as mock_release, \
             patch("handlers.post_tool.ContextInjector") as mock_context:
            mock_manager.return_value.is_workflow_active.return_value = True

            mock_context_instance = MagicMock()
            mock_context.return_value = mock_context_instance

            handler = PostToolHandler()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "plan"},
            }
            handler.run(hook_input)

            mock_context_instance.run.assert_called_once_with(hook_input)

    def test_run_routes_skill_to_deliverable_tracker(self):
        """Verify Skill → deliverable tracker."""
        with patch("handlers.post_tool.get_manager") as mock_manager, \
             patch("handlers.post_tool.PhaseTracker") as mock_phase, \
             patch("handlers.post_tool.DeliverableTracker") as mock_deliverable, \
             patch("handlers.post_tool.ReleasePlanTracker") as mock_release, \
             patch("handlers.post_tool.ContextInjector") as mock_context:
            mock_manager.return_value.is_workflow_active.return_value = True

            mock_deliverable_instance = MagicMock()
            mock_deliverable.return_value = mock_deliverable_instance

            handler = PostToolHandler()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "commit"},
            }
            handler.run(hook_input)

            mock_deliverable_instance.run.assert_called_once_with(hook_input)

    def test_run_routes_write_edit_read_to_deliverable_tracker(self):
        """Verify Write/Edit/Read → deliverable tracker."""
        for tool_name in ["Write", "Edit", "Read", "Bash"]:
            with patch("handlers.post_tool.get_manager") as mock_manager, \
                 patch("handlers.post_tool.PhaseTracker") as mock_phase, \
                 patch("handlers.post_tool.DeliverableTracker") as mock_deliverable, \
                 patch("handlers.post_tool.ReleasePlanTracker") as mock_release, \
                 patch("handlers.post_tool.ContextInjector") as mock_context:
                mock_manager.return_value.is_workflow_active.return_value = True

                mock_deliverable_instance = MagicMock()
                mock_deliverable.return_value = mock_deliverable_instance

                handler = PostToolHandler()
                hook_input = {
                    "hook_event_name": "PostToolUse",
                    "tool_name": tool_name,
                    "tool_input": {"file_path": "/some/file.ts"} if tool_name != "Bash"
                                  else {"command": "npm test"},
                }
                handler.run(hook_input)

                mock_deliverable_instance.run.assert_called_once_with(hook_input)

    def test_run_exits_early_when_inactive(self, inactive_handler):
        """Verify exits when workflow inactive."""
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "explore"},
        }
        with pytest.raises(SystemExit) as exc_info:
            inactive_handler.run(hook_input)
        assert exc_info.value.code == 0

    def test_run_ignores_non_post_tool_use_events(self, handler):
        """Verify ignores other events."""
        with patch("handlers.post_tool.get_manager") as mock_manager, \
             patch("handlers.post_tool.PhaseTracker") as mock_phase, \
             patch("handlers.post_tool.DeliverableTracker") as mock_deliverable, \
             patch("handlers.post_tool.ReleasePlanTracker") as mock_release, \
             patch("handlers.post_tool.ContextInjector") as mock_context:
            mock_manager.return_value.is_workflow_active.return_value = True

            mock_phase_instance = MagicMock()
            mock_phase.return_value = mock_phase_instance

            handler = PostToolHandler()
            hook_input = {
                "hook_event_name": "PreToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "explore"},
            }
            handler.run(hook_input)

            # Should not call any trackers
            mock_phase_instance.run.assert_not_called()

    def test_run_ignores_unsupported_tools(self):
        """Verify ignores unsupported tools like Task."""
        with patch("handlers.post_tool.get_manager") as mock_manager, \
             patch("handlers.post_tool.PhaseTracker") as mock_phase, \
             patch("handlers.post_tool.DeliverableTracker") as mock_deliverable, \
             patch("handlers.post_tool.ReleasePlanTracker") as mock_release, \
             patch("handlers.post_tool.ContextInjector") as mock_context:
            mock_manager.return_value.is_workflow_active.return_value = True

            mock_phase_instance = MagicMock()
            mock_deliverable_instance = MagicMock()
            mock_phase.return_value = mock_phase_instance
            mock_deliverable.return_value = mock_deliverable_instance

            handler = PostToolHandler()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Task",
                "tool_input": {"subagent_type": "Explore"},
            }
            handler.run(hook_input)

            # Should not call any trackers
            mock_phase_instance.run.assert_not_called()
            mock_deliverable_instance.run.assert_not_called()

    def test_run_routes_skill_to_release_plan_tracker(self):
        """Verify Skill → release plan tracker."""
        with patch("handlers.post_tool.get_manager") as mock_manager, \
             patch("handlers.post_tool.PhaseTracker") as mock_phase, \
             patch("handlers.post_tool.DeliverableTracker") as mock_deliverable, \
             patch("handlers.post_tool.ReleasePlanTracker") as mock_release, \
             patch("handlers.post_tool.ContextInjector") as mock_context:
            mock_manager.return_value.is_workflow_active.return_value = True

            mock_release_instance = MagicMock()
            mock_release.return_value = mock_release_instance

            handler = PostToolHandler()
            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "log:task", "args": "T001 completed"},
            }
            handler.run(hook_input)

            mock_release_instance.run_post_tool.assert_called_once_with(hook_input)


class TestHandlePostToolFunction:
    """Tests for handle_post_tool convenience function."""

    def test_handle_post_tool_works(self):
        """Verify handle_post_tool function works correctly."""
        with patch("handlers.post_tool.get_manager") as mock_manager, \
             patch("handlers.post_tool.PhaseTracker"), \
             patch("handlers.post_tool.DeliverableTracker"), \
             patch("handlers.post_tool.ReleasePlanTracker"), \
             patch("handlers.post_tool.ContextInjector"):
            mock_manager.return_value.is_workflow_active.return_value = False

            hook_input = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "/some/file.ts"},
            }

            with pytest.raises(SystemExit) as exc_info:
                handle_post_tool(hook_input)
            assert exc_info.value.code == 0


class TestImports:
    """Tests for module imports."""

    def test_handler_import(self):
        """PostToolHandler can be imported."""
        from handlers.post_tool import PostToolHandler
        assert PostToolHandler is not None

    def test_function_import(self):
        """handle_post_tool function can be imported."""
        from handlers.post_tool import handle_post_tool
        assert callable(handle_post_tool)

    def test_main_import(self):
        """main function can be imported."""
        from handlers.post_tool import main
        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
