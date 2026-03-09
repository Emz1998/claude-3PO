"""Tests for handlers — recorder, reminders, initialize_state."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

import pytest

from workflow.models.hook_input import PostToolUseInput, PreToolUseInput, UserPromptSubmitInput
from helpers import make_post_tool_input, make_pre_tool_input, make_user_prompt_input


# ─── Recorder ────────────────────────────────────────────────────────────────


class TestRecorder:
    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_record_explore_agent(self, mock_store):
        """record_agent_invoked sets explore_agent_invoked."""
        from workflow.handlers.recorder import record_agent_invoked
        record_agent_invoked("Explore")
        mock_store.set.assert_called_with("explore_agent_invoked", True)

    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_record_plan_agent(self, mock_store):
        from workflow.handlers.recorder import record_agent_invoked
        record_agent_invoked("Plan")
        mock_store.set.assert_called_with("plan_agent_invoked", True)

    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_record_plan_reviewer_agent(self, mock_store):
        from workflow.handlers.recorder import record_agent_invoked
        record_agent_invoked("PlanReviewer")
        mock_store.set.assert_called_with("plan_reviewer_agent_invoked", True)

    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_record_test_engineer_agent(self, mock_store):
        from workflow.handlers.recorder import record_agent_invoked
        record_agent_invoked("TestEngineer")
        mock_store.set.assert_called_with("test_engineer_agent_invoked", True)

    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_record_test_reviewer_agent(self, mock_store):
        from workflow.handlers.recorder import record_agent_invoked
        record_agent_invoked("TestReviewer")
        mock_store.set.assert_called_with("test_reviewer_agent_invoked", True)

    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_record_code_reviewer_agent(self, mock_store):
        from workflow.handlers.recorder import record_agent_invoked
        record_agent_invoked("CodeReviewer")
        mock_store.set.assert_called_with("code_reviewer_agent_invoked", True)

    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_record_unknown_agent_skips(self, mock_store):
        """Unknown agent name does nothing."""
        from workflow.handlers.recorder import record_agent_invoked
        record_agent_invoked("UnknownAgent")
        mock_store.set.assert_not_called()

    @patch("workflow.handlers.recorder.STATE_STORE")
    @patch("workflow.handlers.recorder.cfg")
    def test_record_plan_file_created(self, mock_cfg, mock_store):
        """Write in plans dir records plan_file_created."""
        mock_cfg.return_value = "~/.claude/plans"
        from workflow.handlers.recorder import record_plan_file_created
        plans_dir = str(Path("~/.claude/plans").expanduser())
        file_path = str(Path(plans_dir) / "my-plan.md")
        record_plan_file_created("Write", file_path)
        mock_store.set.assert_called_with("plan_file_created", True)

    @patch("workflow.handlers.recorder.STATE_STORE")
    @patch("workflow.handlers.recorder.cfg")
    def test_record_plan_file_wrong_dir_skips(self, mock_cfg, mock_store):
        """Write outside plans dir does nothing."""
        mock_cfg.return_value = "~/.claude/plans"
        from workflow.handlers.recorder import record_plan_file_created
        record_plan_file_created("Write", "/tmp/other/file.md")
        mock_store.set.assert_not_called()

    @patch("workflow.handlers.recorder.STATE_STORE")
    @patch("workflow.handlers.recorder.cfg")
    def test_record_plan_file_non_write_skips(self, mock_cfg, mock_store):
        """Non-Write tool does nothing."""
        mock_cfg.return_value = "~/.claude/plans"
        from workflow.handlers.recorder import record_plan_file_created
        record_plan_file_created("Edit", "/plans/my-plan.md")
        mock_store.set.assert_not_called()

    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_recorder_main_enter_plan_mode(self, mock_store):
        """main() records enter_plan_mode_triggered on EnterPlanMode."""
        data = make_post_tool_input("EnterPlanMode", {})
        with patch("workflow.handlers.recorder.Hook") as MockHook:
            MockHook.read_stdin.return_value = data
            from workflow.handlers.recorder import main
            main()
        mock_store.set.assert_called_with("enter_plan_mode_triggered", True)


# ─── Reminders ───────────────────────────────────────────────────────────────


class TestReminders:
    def test_run_no_match_returns(self):
        """No matching reminder returns without sending."""
        data = make_pre_tool_input("Read", {"file_path": "/tmp/x", "offset": 0, "limit": 100})
        hook_input = PreToolUseInput.model_validate(data)

        with patch("workflow.handlers.reminders.REMINDERS_MAP", {}):
            from workflow.handlers.reminders import Reminders
            r = Reminders(hook_input)
            # Should return without calling sys.exit
            r.run()

    def test_run_matching_sends(self, tmp_path):
        """Matching reminder loads template and sends."""
        tpl_file = tmp_path / "test_reminder.md"
        tpl_file.write_text("Do the thing!")

        data = make_post_tool_input("EnterPlanMode", {})
        hook_input = PostToolUseInput.model_validate(data)

        reminders_map = {("PostToolUse", "EnterPlanMode", None): "test_reminder.md"}

        with patch("workflow.handlers.reminders.REMINDERS_MAP", reminders_map), \
             patch("workflow.handlers.reminders.REMINDERS_DIR", tmp_path):
            from workflow.handlers.reminders import Reminders
            r = Reminders(hook_input)
            with pytest.raises(SystemExit) as exc:
                r.run()
            assert exc.value.code == 0


# ─── Initialize State ────────────────────────────────────────────────────────


class TestInitializeState:
    @patch("workflow.initialize_state.cfg", return_value=".claude/hooks/workflow/state.json")
    def test_initialize_state(self, mock_cfg):
        """initialize_state saves correct initial keys."""
        mock_store = MagicMock()
        with patch("workflow.initialize_state.StateStore", return_value=mock_store):
            from workflow.initialize_state import initialize_state
            data = make_user_prompt_input("test")
            hook_input = UserPromptSubmitInput.model_validate(data)
            initialize_state(hook_input)
        mock_store.save.assert_called_once_with({
            "recent_phase": "",
            "recent_coding_phase": "",
        })
