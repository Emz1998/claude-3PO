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
    def test_record_recent_agent_explore(self, mock_store):
        """record_recent_agent records agent name as recent_agent."""
        from workflow.handlers.recorder import record_recent_agent
        record_recent_agent("Explore")
        mock_store.set.assert_called_with("recent_agent", "Explore")

    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_record_recent_agent_plan(self, mock_store):
        from workflow.handlers.recorder import record_recent_agent
        record_recent_agent("Plan")
        mock_store.set.assert_called_with("recent_agent", "Plan")

    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_record_recent_agent_plan_reviewer(self, mock_store):
        from workflow.handlers.recorder import record_recent_agent
        record_recent_agent("PlanReviewer")
        mock_store.set.assert_called_with("recent_agent", "PlanReviewer")

    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_record_recent_agent_test_engineer(self, mock_store):
        from workflow.handlers.recorder import record_recent_agent
        record_recent_agent("TestEngineer")
        mock_store.set.assert_called_with("recent_agent", "TestEngineer")

    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_record_recent_agent_code_reviewer(self, mock_store):
        from workflow.handlers.recorder import record_recent_agent
        record_recent_agent("CodeReviewer")
        mock_store.set.assert_called_with("recent_agent", "CodeReviewer")

    @patch("workflow.handlers.recorder.STATE_STORE")
    def test_record_recent_agent_unknown(self, mock_store):
        """Any agent name is recorded (no filtering)."""
        from workflow.handlers.recorder import record_recent_agent
        record_recent_agent("UnknownAgent")
        mock_store.set.assert_called_with("recent_agent", "UnknownAgent")

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


# ─── PrRecorder ─────────────────────────────────────────────────────────────


class TestPrRecorder:
    @patch("workflow.handlers.pr_recorder.check_workflow_gate", return_value=True)
    @patch("workflow.handlers.pr_recorder.cfg", return_value=".claude/hooks/workflow/state.json")
    @patch("workflow.handlers.pr_recorder.StateStore")
    def test_gh_pr_create_sets_state(self, MockStore, mock_cfg, mock_gate):
        """Detects gh pr create and sets pr_created=True."""
        mock_store = MagicMock()
        MockStore.return_value = mock_store

        data = make_post_tool_input("Bash", {"command": "gh pr create --title test", "description": "Create PR"})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.pr_recorder import PrRecorder
        PrRecorder(hook_input).run()
        mock_store.set.assert_called_once_with("pr_created", True)

    @patch("workflow.handlers.pr_recorder.check_workflow_gate", return_value=True)
    def test_non_bash_tool_skips(self, mock_gate):
        """Non-Bash tool does not record anything."""
        data = make_post_tool_input("Skill", {"skill": "commit", "args": ""})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.pr_recorder import PrRecorder
        PrRecorder(hook_input).run()  # Should not raise or set state

    @patch("workflow.handlers.pr_recorder.check_workflow_gate", return_value=True)
    def test_bash_without_gh_pr_create_skips(self, mock_gate):
        """Bash command without gh pr create does not set state."""
        data = make_post_tool_input("Bash", {"command": "git push origin main", "description": "Push"})
        hook_input = PostToolUseInput.model_validate(data)

        with patch("workflow.handlers.pr_recorder.StateStore") as MockStore:
            from workflow.handlers.pr_recorder import PrRecorder
            PrRecorder(hook_input).run()
            MockStore.return_value.set.assert_not_called()

    @patch("workflow.handlers.pr_recorder.check_workflow_gate", return_value=False)
    def test_inactive_workflow_skips(self, mock_gate):
        """Inactive workflow skips recorder."""
        data = make_post_tool_input("Bash", {"command": "gh pr create --title test", "description": "Create PR"})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.pr_recorder import PrRecorder
        PrRecorder(hook_input).run()  # Should not raise


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
