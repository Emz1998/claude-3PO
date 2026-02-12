#!/usr/bin/env python3
"""Pytest tests for the user_prompt handler module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handlers.user_prompt import UserPromptHandler, handle_user_prompt  # type: ignore


@pytest.fixture
def handler():
    """Provide a handler instance with mocked dependencies."""
    with patch("handlers.user_prompt.get_manager") as mock_manager, \
         patch("handlers.user_prompt.get_triggers") as mock_triggers:
        mock_manager.return_value.is_workflow_active.return_value = False
        mock_manager.return_value.is_dry_run_active.return_value = False
        mock_manager.return_value.is_troubleshoot_active.return_value = False
        mock_manager.return_value.activate_workflow = MagicMock()
        mock_manager.return_value.deactivate_workflow = MagicMock()
        mock_manager.return_value.activate_dry_run = MagicMock()
        mock_manager.return_value.reset = MagicMock()
        mock_manager.return_value.reset_deliverables_status = MagicMock()
        mock_manager.return_value.get = MagicMock(side_effect=lambda k, d=None: d)
        mock_manager.return_value.delete = MagicMock()

        # Setup triggers config - use T\d{3} pattern (matching workflow.config.yaml)
        mock_implement = MagicMock()
        mock_implement.command = "/implement"
        mock_implement.arg_pattern = r"T\d{3}(\s*-\s*T\d{3})?$"

        mock_deactivate = MagicMock()
        mock_deactivate.command = "/deactivate-workflow"

        mock_dry_run = MagicMock()
        mock_dry_run.command = "/dry-run"

        mock_troubleshoot = MagicMock()
        mock_troubleshoot.command = "/troubleshoot"

        mock_triggers.return_value.implement = mock_implement
        mock_triggers.return_value.deactivate = mock_deactivate
        mock_triggers.return_value.dry_run = mock_dry_run
        mock_triggers.return_value.troubleshoot = mock_troubleshoot

        yield UserPromptHandler()


class TestIsImplementTriggered:
    """Tests for is_implement_triggered method."""

    def test_is_implement_triggered_detects_command(self, handler):
        """Detects /implement in prompt."""
        assert handler.is_implement_triggered("/implement T001") is True
        assert handler.is_implement_triggered("Please /implement T002") is True

    def test_is_implement_triggered_returns_false_when_not_present(self, handler):
        """Returns False when /implement not in prompt."""
        assert handler.is_implement_triggered("Hello world") is False
        assert handler.is_implement_triggered("/deactivate-workflow") is False


class TestParseTaskIds:
    """Tests for _parse_task_ids method."""

    def test_parse_no_args_returns_empty(self, handler):
        """No args returns empty list."""
        assert handler._parse_task_ids("/implement") == []

    def test_parse_single_task(self, handler):
        """Single task ID parsed correctly."""
        assert handler._parse_task_ids("/implement T009") == ["T009"]

    def test_parse_task_range(self, handler):
        """Task range parsed correctly."""
        assert handler._parse_task_ids("/implement T009 - T011") == [
            "T009",
            "T010",
            "T011",
        ]

    def test_parse_task_range_no_spaces(self, handler):
        """Task range without spaces parsed correctly."""
        assert handler._parse_task_ids("/implement T009-T011") == [
            "T009",
            "T010",
            "T011",
        ]

    def test_parse_invalid_format_returns_empty(self, handler):
        """Invalid format returns empty list."""
        assert handler._parse_task_ids("/implement invalid") == []
        assert handler._parse_task_ids("/implement T00") == []  # Too short

    def test_parse_reversed_range_returns_empty(self, handler):
        """Reversed range (end < start) returns empty."""
        assert handler._parse_task_ids("/implement T010 - T005") == []


class TestValidateTasksInCurrent:
    """Tests for _validate_tasks_in_current method."""

    def test_empty_list_is_valid(self, handler):
        """Empty list (no args case) is valid."""
        is_valid, msg = handler._validate_tasks_in_current([])
        assert is_valid is True
        assert msg == ""

    def test_valid_task_in_current(self, handler):
        """Task in current_tasks is valid."""
        with patch(
            "handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]
        ):
            # Need to reimport to pick up the mock
            from handlers.user_prompt import UserPromptHandler

            with patch("handlers.user_prompt.get_manager"), patch(
                "handlers.user_prompt.get_triggers"
            ) as mock_triggers:
                mock_implement = MagicMock()
                mock_implement.command = "/implement"
                mock_triggers.return_value.implement = mock_implement
                h = UserPromptHandler()
                is_valid, msg = h._validate_tasks_in_current(["T009"])
                assert is_valid is True

    def test_invalid_task_not_in_current(self, handler):
        """Task not in current_tasks is invalid."""
        with patch(
            "handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]
        ):
            from handlers.user_prompt import UserPromptHandler

            with patch("handlers.user_prompt.get_manager"), patch(
                "handlers.user_prompt.get_triggers"
            ) as mock_triggers:
                mock_implement = MagicMock()
                mock_implement.command = "/implement"
                mock_triggers.return_value.implement = mock_implement
                h = UserPromptHandler()
                is_valid, msg = h._validate_tasks_in_current(["T001"])
                assert is_valid is False
                assert "T001" in msg

    def test_partial_range_invalid(self, handler):
        """Range with some tasks not in current_tasks is invalid."""
        with patch(
            "handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]
        ):
            from handlers.user_prompt import UserPromptHandler

            with patch("handlers.user_prompt.get_manager"), patch(
                "handlers.user_prompt.get_triggers"
            ) as mock_triggers:
                mock_implement = MagicMock()
                mock_implement.command = "/implement"
                mock_triggers.return_value.implement = mock_implement
                h = UserPromptHandler()
                is_valid, msg = h._validate_tasks_in_current(["T009", "T010", "T011"])
                assert is_valid is False
                assert "T011" in msg

    def test_no_current_tasks_is_invalid(self, handler):
        """No current tasks available is invalid."""
        with patch("handlers.user_prompt.get_current_tasks_ids", return_value=[]):
            from handlers.user_prompt import UserPromptHandler

            with patch("handlers.user_prompt.get_manager"), patch(
                "handlers.user_prompt.get_triggers"
            ) as mock_triggers:
                mock_implement = MagicMock()
                mock_implement.command = "/implement"
                mock_triggers.return_value.implement = mock_implement
                h = UserPromptHandler()
                is_valid, msg = h._validate_tasks_in_current(["T009"])
                assert is_valid is False
                assert "No current tasks" in msg


class TestIsValidImplementArgs:
    """Tests for is_valid_implement_args method."""

    def test_no_args_is_valid(self, handler):
        """No arguments is valid (defaults to current tasks)."""
        assert handler.is_valid_implement_args("/implement") is True

    def test_valid_task_is_valid(self, handler):
        """Valid task in current_tasks is valid."""
        with patch(
            "handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]
        ):
            from handlers.user_prompt import UserPromptHandler

            with patch("handlers.user_prompt.get_manager"), patch(
                "handlers.user_prompt.get_triggers"
            ) as mock_triggers:
                mock_implement = MagicMock()
                mock_implement.command = "/implement"
                mock_triggers.return_value.implement = mock_implement
                h = UserPromptHandler()
                assert h.is_valid_implement_args("/implement T009") is True

    def test_valid_range_is_valid(self, handler):
        """Valid range within current_tasks is valid."""
        with patch(
            "handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]
        ):
            from handlers.user_prompt import UserPromptHandler

            with patch("handlers.user_prompt.get_manager"), patch(
                "handlers.user_prompt.get_triggers"
            ) as mock_triggers:
                mock_implement = MagicMock()
                mock_implement.command = "/implement"
                mock_triggers.return_value.implement = mock_implement
                h = UserPromptHandler()
                assert h.is_valid_implement_args("/implement T009 - T010") is True

    def test_invalid_task_is_invalid(self, handler):
        """Task not in current_tasks is invalid."""
        with patch(
            "handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]
        ):
            from handlers.user_prompt import UserPromptHandler

            with patch("handlers.user_prompt.get_manager"), patch(
                "handlers.user_prompt.get_triggers"
            ) as mock_triggers:
                mock_implement = MagicMock()
                mock_implement.command = "/implement"
                mock_triggers.return_value.implement = mock_implement
                h = UserPromptHandler()
                assert h.is_valid_implement_args("/implement T001") is False

    def test_out_of_range_is_invalid(self, handler):
        """Range extending beyond current_tasks is invalid."""
        with patch(
            "handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]
        ):
            from handlers.user_prompt import UserPromptHandler

            with patch("handlers.user_prompt.get_manager"), patch(
                "handlers.user_prompt.get_triggers"
            ) as mock_triggers:
                mock_implement = MagicMock()
                mock_implement.command = "/implement"
                mock_triggers.return_value.implement = mock_implement
                h = UserPromptHandler()
                assert h.is_valid_implement_args("/implement T009 - T015") is False

    def test_invalid_format_is_invalid(self, handler):
        """Invalid format is invalid."""
        assert handler.is_valid_implement_args("/implement invalid") is False

    def test_non_implement_command_is_valid(self, handler):
        """Non-implement commands pass through."""
        assert handler.is_valid_implement_args("/other-command") is True

    def test_help_flag_is_valid(self, handler):
        """Help flag is valid."""
        assert handler.is_valid_implement_args("/implement --help") is True
        assert handler.is_valid_implement_args("/implement -h") is True


class TestIsHelpRequested:
    """Tests for is_help_requested method."""

    def test_help_flag_detected(self, handler):
        """--help flag is detected."""
        assert handler.is_help_requested("/implement --help") is True

    def test_short_help_flag_detected(self, handler):
        """Short -h flag is detected."""
        assert handler.is_help_requested("/implement -h") is True

    def test_no_help_flag(self, handler):
        """No help flag returns False."""
        assert handler.is_help_requested("/implement") is False
        assert handler.is_help_requested("/implement T001") is False


class TestIsContinueRequested:
    """Tests for is_continue_requested method."""

    def test_continue_flag_detected(self, handler):
        """--continue flag is detected."""
        assert handler.is_continue_requested("/implement --continue") is True

    def test_short_continue_flag_detected(self, handler):
        """Short -c flag is detected."""
        assert handler.is_continue_requested("/implement -c") is True

    def test_no_continue_flag(self, handler):
        """No continue flag returns False."""
        assert handler.is_continue_requested("/implement") is False
        assert handler.is_continue_requested("/implement T001") is False


class TestGetResolvedTaskIds:
    """Tests for get_resolved_task_ids method."""

    def test_no_args_returns_current_tasks(self, handler):
        """No args returns all current tasks."""
        with patch(
            "handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]
        ):
            from handlers.user_prompt import UserPromptHandler

            with patch("handlers.user_prompt.get_manager"), patch(
                "handlers.user_prompt.get_triggers"
            ) as mock_triggers:
                mock_implement = MagicMock()
                mock_implement.command = "/implement"
                mock_triggers.return_value.implement = mock_implement
                h = UserPromptHandler()
                assert h.get_resolved_task_ids("/implement") == ["T009", "T010"]

    def test_single_task_returns_list(self, handler):
        """Single task returns list with that task."""
        assert handler.get_resolved_task_ids("/implement T009") == ["T009"]

    def test_range_returns_expanded_list(self, handler):
        """Range returns expanded list of tasks."""
        assert handler.get_resolved_task_ids("/implement T009 - T011") == [
            "T009",
            "T010",
            "T011",
        ]


class TestIsDeactivateTriggered:
    """Tests for is_deactivate_triggered method."""

    def test_is_deactivate_triggered_detects_command(self, handler):
        """Detects /deactivate-workflow in prompt."""
        assert handler.is_deactivate_triggered("/deactivate-workflow") is True
        assert handler.is_deactivate_triggered("Please /deactivate-workflow") is True

    def test_is_deactivate_triggered_returns_false_when_not_present(self, handler):
        """Returns False when /deactivate-workflow not in prompt."""
        assert handler.is_deactivate_triggered("Hello world") is False


class TestIsDryRunTriggered:
    """Tests for is_dry_run_triggered method."""

    def test_is_dry_run_triggered_detects_command(self, handler):
        """Detects /dry-run in prompt."""
        assert handler.is_dry_run_triggered("/dry-run") is True
        assert handler.is_dry_run_triggered("/dry-run:explore") is True

    def test_is_dry_run_triggered_returns_false_when_not_present(self, handler):
        """Returns False when /dry-run not in prompt."""
        assert handler.is_dry_run_triggered("Hello world") is False


class TestHandleContinue:
    """Tests for handle_continue method."""

    def test_continue_reactivates_when_stopped(self):
        """Continue reactivates workflow when stopped."""
        with patch("handlers.user_prompt.get_manager") as mock_manager, \
             patch("handlers.user_prompt.get_triggers") as mock_triggers:
            mock_state = MagicMock()
            mock_state.is_workflow_active.return_value = False
            mock_state.get.side_effect = lambda k, d=None: {
                "stopped_phase": "explore",
                "stopped_at": "2026-02-04T10:00:00"
            }.get(k, d)
            mock_manager.return_value = mock_state

            mock_implement = MagicMock()
            mock_implement.command = "/implement"
            mock_triggers.return_value.implement = mock_implement

            handler = UserPromptHandler()
            handler.handle_continue()

            mock_state.activate_workflow.assert_called_once()
            mock_state.delete.assert_any_call("stopped_at")
            mock_state.delete.assert_any_call("stopped_phase")
            mock_state.delete.assert_any_call("stop_hook_active")

    def test_continue_blocks_when_already_active(self):
        """Continue blocks when workflow already active."""
        with patch("handlers.user_prompt.get_manager") as mock_manager, \
             patch("handlers.user_prompt.get_triggers") as mock_triggers:
            mock_state = MagicMock()
            mock_state.is_workflow_active.return_value = True
            mock_manager.return_value = mock_state

            mock_implement = MagicMock()
            mock_implement.command = "/implement"
            mock_triggers.return_value.implement = mock_implement

            handler = UserPromptHandler()

            with pytest.raises(SystemExit) as exc_info:
                handler.handle_continue()

            assert exc_info.value.code == 2


class TestHandleImplement:
    """Tests for handle_implement method."""

    def test_handle_implement_resets_and_activates_workflow(self):
        """Resets state and activates workflow on valid /implement with no args."""
        with patch("handlers.user_prompt.get_manager") as mock_manager, \
             patch("handlers.user_prompt.get_triggers") as mock_triggers, \
             patch("handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]):
            mock_state = MagicMock()
            mock_state.is_workflow_active.return_value = False
            mock_state.is_dry_run_active.return_value = False
            mock_manager.return_value = mock_state

            mock_implement = MagicMock()
            mock_implement.command = "/implement"
            mock_implement.arg_pattern = r"T\d{3}(\s*-\s*T\d{3})?$"
            mock_triggers.return_value.implement = mock_implement
            mock_triggers.return_value.deactivate = MagicMock()
            mock_triggers.return_value.dry_run = MagicMock()

            handler = UserPromptHandler()
            handler.handle_implement("/implement")

            mock_state.reset.assert_called_once()
            mock_state.activate_workflow.assert_called_once()

    def test_handle_implement_activates_workflow_with_task(self):
        """Activates workflow on valid /implement with task ID."""
        with patch("handlers.user_prompt.get_manager") as mock_manager, \
             patch("handlers.user_prompt.get_triggers") as mock_triggers, \
             patch("handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]):
            mock_state = MagicMock()
            mock_state.is_workflow_active.return_value = False
            mock_state.is_dry_run_active.return_value = False
            mock_manager.return_value = mock_state

            mock_implement = MagicMock()
            mock_implement.command = "/implement"
            mock_implement.arg_pattern = r"T\d{3}(\s*-\s*T\d{3})?$"
            mock_triggers.return_value.implement = mock_implement
            mock_triggers.return_value.deactivate = MagicMock()
            mock_triggers.return_value.dry_run = MagicMock()

            handler = UserPromptHandler()
            handler.handle_implement("/implement T009")

            mock_state.reset.assert_called_once()
            mock_state.activate_workflow.assert_called_once()

    def test_handle_implement_exits_on_invalid_task(self):
        """Exits with code 2 when task not in current_tasks."""
        with patch("handlers.user_prompt.get_manager") as mock_manager, \
             patch("handlers.user_prompt.get_triggers") as mock_triggers, \
             patch("handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]):
            mock_manager.return_value.is_workflow_active.return_value = False

            mock_implement = MagicMock()
            mock_implement.command = "/implement"
            mock_implement.arg_pattern = r"T\d{3}(\s*-\s*T\d{3})?$"
            mock_triggers.return_value.implement = mock_implement
            mock_triggers.return_value.deactivate = MagicMock()
            mock_triggers.return_value.dry_run = MagicMock()

            handler = UserPromptHandler()

            with pytest.raises(SystemExit) as exc_info:
                handler.handle_implement("/implement T001")
            assert exc_info.value.code == 2


class TestHandleDeactivate:
    """Tests for handle_deactivate method."""

    def test_handle_deactivate_deactivates_workflow(self):
        """Deactivates workflow."""
        with patch("handlers.user_prompt.get_manager") as mock_manager, \
             patch("handlers.user_prompt.get_triggers") as mock_triggers:
            mock_state = MagicMock()
            mock_manager.return_value = mock_state

            mock_triggers.return_value.implement = MagicMock()
            mock_triggers.return_value.deactivate = MagicMock()
            mock_triggers.return_value.dry_run = MagicMock()

            handler = UserPromptHandler()
            handler.handle_deactivate()

            mock_state.deactivate_workflow.assert_called_once()


class TestHandleDryRun:
    """Tests for handle_dry_run method."""

    def test_handle_dry_run_activates_dry_run_mode(self):
        """Activates dry run mode when not active."""
        with patch("handlers.user_prompt.get_manager") as mock_manager, \
             patch("handlers.user_prompt.get_triggers") as mock_triggers:
            mock_state = MagicMock()
            mock_state.is_dry_run_active.return_value = False
            mock_manager.return_value = mock_state

            mock_triggers.return_value.implement = MagicMock()
            mock_triggers.return_value.deactivate = MagicMock()
            mock_triggers.return_value.dry_run = MagicMock()

            handler = UserPromptHandler()
            handler.handle_dry_run()

            mock_state.reset.assert_called_once()
            mock_state.activate_workflow.assert_called_once()
            mock_state.activate_dry_run.assert_called_once()

    def test_handle_dry_run_resets_deliverables_when_already_active(self):
        """Resets deliverables when dry run already active."""
        with patch("handlers.user_prompt.get_manager") as mock_manager, \
             patch("handlers.user_prompt.get_triggers") as mock_triggers:
            mock_state = MagicMock()
            mock_state.is_dry_run_active.return_value = True
            mock_manager.return_value = mock_state

            mock_triggers.return_value.implement = MagicMock()
            mock_triggers.return_value.deactivate = MagicMock()
            mock_triggers.return_value.dry_run = MagicMock()

            handler = UserPromptHandler()
            handler.handle_dry_run()

            mock_state.reset_deliverables_status.assert_called_once()
            mock_state.reset.assert_not_called()


class TestRun:
    """Tests for run method."""

    def test_run_exits_early_for_non_user_prompt_event(self, handler):
        """Exits for non-UserPromptSubmit events."""
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "explore"},
        }
        with pytest.raises(SystemExit) as exc_info:
            handler.run(hook_input)
        assert exc_info.value.code == 0

    def test_run_exits_early_for_empty_prompt(self, handler):
        """Exits for empty prompt."""
        hook_input = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "",
        }
        with pytest.raises(SystemExit) as exc_info:
            handler.run(hook_input)
        assert exc_info.value.code == 0

    def test_run_handles_implement_command(self):
        """Handles /implement command."""
        with patch("handlers.user_prompt.get_manager") as mock_manager, \
             patch("handlers.user_prompt.get_triggers") as mock_triggers, \
             patch("handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]):
            mock_state = MagicMock()
            mock_state.is_workflow_active.return_value = False
            mock_state.is_dry_run_active.return_value = False
            mock_manager.return_value = mock_state

            mock_implement = MagicMock()
            mock_implement.command = "/implement"
            mock_implement.arg_pattern = r"T\d{3}(\s*-\s*T\d{3})?$"
            mock_deactivate = MagicMock()
            mock_deactivate.command = "/deactivate-workflow"
            mock_dry_run = MagicMock()
            mock_dry_run.command = "/dry-run"
            mock_troubleshoot = MagicMock()
            mock_troubleshoot.command = "/troubleshoot"

            mock_triggers.return_value.implement = mock_implement
            mock_triggers.return_value.deactivate = mock_deactivate
            mock_triggers.return_value.dry_run = mock_dry_run
            mock_triggers.return_value.troubleshoot = mock_troubleshoot

            handler = UserPromptHandler()
            hook_input = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "/implement T009",
            }
            handler.run(hook_input)

            mock_state.activate_workflow.assert_called_once()

    def test_run_handles_deactivate_command(self):
        """Handles /deactivate-workflow command."""
        with patch("handlers.user_prompt.get_manager") as mock_manager, \
             patch("handlers.user_prompt.get_triggers") as mock_triggers:
            mock_state = MagicMock()
            mock_manager.return_value = mock_state

            mock_implement = MagicMock()
            mock_implement.command = "/implement"
            mock_deactivate = MagicMock()
            mock_deactivate.command = "/deactivate-workflow"
            mock_dry_run = MagicMock()
            mock_dry_run.command = "/dry-run"

            mock_triggers.return_value.implement = mock_implement
            mock_triggers.return_value.deactivate = mock_deactivate
            mock_triggers.return_value.dry_run = mock_dry_run

            handler = UserPromptHandler()
            hook_input = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "/deactivate-workflow",
            }
            handler.run(hook_input)

            mock_state.deactivate_workflow.assert_called_once()

    def test_run_blocks_invalid_implement_args(self):
        """Blocks /implement with invalid task (not in current_tasks)."""
        with patch("handlers.user_prompt.get_manager") as mock_manager, \
             patch("handlers.user_prompt.get_triggers") as mock_triggers, \
             patch("handlers.user_prompt.get_current_tasks_ids", return_value=["T009", "T010"]):
            mock_manager.return_value.is_workflow_active.return_value = False

            mock_implement = MagicMock()
            mock_implement.command = "/implement"
            mock_implement.arg_pattern = r"T\d{3}(\s*-\s*T\d{3})?$"
            mock_deactivate = MagicMock()
            mock_deactivate.command = "/deactivate-workflow"
            mock_dry_run = MagicMock()
            mock_dry_run.command = "/dry-run"
            mock_troubleshoot = MagicMock()
            mock_troubleshoot.command = "/troubleshoot"

            mock_triggers.return_value.implement = mock_implement
            mock_triggers.return_value.deactivate = mock_deactivate
            mock_triggers.return_value.dry_run = mock_dry_run
            mock_triggers.return_value.troubleshoot = mock_troubleshoot

            handler = UserPromptHandler()
            hook_input = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "/implement T001",
            }

            with pytest.raises(SystemExit) as exc_info:
                handler.run(hook_input)
            assert exc_info.value.code == 2


class TestHandleUserPromptFunction:
    """Tests for handle_user_prompt convenience function."""

    def test_handle_user_prompt_works(self):
        """Verify handle_user_prompt function works correctly."""
        with patch("handlers.user_prompt.get_manager") as mock_manager, \
             patch("handlers.user_prompt.get_triggers") as mock_triggers:
            mock_manager.return_value.is_workflow_active.return_value = False

            mock_triggers.return_value.implement = MagicMock()
            mock_triggers.return_value.deactivate = MagicMock()
            mock_triggers.return_value.dry_run = MagicMock()

            hook_input = {
                "hook_event_name": "PreToolUse",
                "prompt": "Hello",
            }

            with pytest.raises(SystemExit) as exc_info:
                handle_user_prompt(hook_input)
            assert exc_info.value.code == 0


class TestImports:
    """Tests for module imports."""

    def test_handler_import(self):
        """UserPromptHandler can be imported."""
        from handlers.user_prompt import UserPromptHandler
        assert UserPromptHandler is not None

    def test_function_import(self):
        """handle_user_prompt function can be imported."""
        from handlers.user_prompt import handle_user_prompt
        assert callable(handle_user_prompt)

    def test_main_import(self):
        """main function can be imported."""
        from handlers.user_prompt import main
        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
