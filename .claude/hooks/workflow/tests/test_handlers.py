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
    @patch("workflow.handlers.recorder.SESSION")
    def test_record_recent_agent_with_story_id(self, mock_session):
        """record_recent_agent updates session phase.recent_agent."""
        mock_session.story_id = "SK-TEST"
        mock_session.update_session = MagicMock()
        from workflow.handlers.recorder import record_recent_agent
        record_recent_agent("Explore")
        mock_session.update_session.assert_called_once()
        args = mock_session.update_session.call_args
        assert args[0][0] == "SK-TEST"

    @patch("workflow.handlers.recorder.SESSION")
    def test_record_recent_agent_no_story_id(self, mock_session):
        """record_recent_agent is no-op when STORY_ID not set."""
        mock_session.story_id = None
        from workflow.handlers.recorder import record_recent_agent
        record_recent_agent("Explore")
        mock_session.update_session.assert_not_called()

    @patch("workflow.handlers.recorder.SESSION")
    @patch("workflow.handlers.recorder.cfg")
    def test_record_plan_file_created(self, mock_cfg, mock_session):
        """Write in plans dir records plan_file_created."""
        mock_cfg.return_value = "~/.claude/plans"
        mock_session.story_id = "SK-TEST"
        mock_session.update_session = MagicMock()
        from workflow.handlers.recorder import record_plan_file_created
        plans_dir = str(Path("~/.claude/plans").expanduser())
        file_path = str(Path(plans_dir) / "my-plan.md")
        record_plan_file_created("Write", file_path)
        mock_session.update_session.assert_called_once()

    @patch("workflow.handlers.recorder.SESSION")
    @patch("workflow.handlers.recorder.cfg")
    def test_record_plan_file_wrong_dir_skips(self, mock_cfg, mock_session):
        """Write outside plans dir does nothing."""
        mock_cfg.return_value = "~/.claude/plans"
        mock_session.story_id = "SK-TEST"
        from workflow.handlers.recorder import record_plan_file_created
        record_plan_file_created("Write", "/tmp/other/file.md")
        mock_session.update_session.assert_not_called()

    @patch("workflow.handlers.recorder.SESSION")
    @patch("workflow.handlers.recorder.cfg")
    def test_record_plan_file_non_write_skips(self, mock_cfg, mock_session):
        """Non-Write tool does nothing."""
        mock_cfg.return_value = "~/.claude/plans"
        mock_session.story_id = "SK-TEST"
        from workflow.handlers.recorder import record_plan_file_created
        record_plan_file_created("Edit", "/plans/my-plan.md")
        mock_session.update_session.assert_not_called()

    @patch("workflow.handlers.recorder.SESSION")
    def test_recorder_main_enter_plan_mode(self, mock_session):
        """main() records pre-coding phase on EnterPlanMode."""
        mock_session.story_id = "SK-TEST"
        mock_session.update_session = MagicMock()
        data = make_post_tool_input("EnterPlanMode", {})
        with patch("workflow.handlers.recorder.Hook") as MockHook:
            MockHook.read_stdin.return_value = data
            from workflow.handlers.recorder import main
            main()
        mock_session.update_session.assert_called_once()


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


# ─── PrRecorder ─────────────────────────────────────────────────────────────


class TestPrRecorder:
    @patch("workflow.handlers.pr_recorder.SessionState")
    @patch("workflow.handlers.pr_recorder.check_workflow_gate", return_value=True)
    def test_gh_pr_create_sets_session(self, mock_gate, MockSession):
        """Detects gh pr create and updates session pr state."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.update_session = MagicMock()
        MockSession.return_value = mock_session

        data = make_post_tool_input("Bash", {"command": "gh pr create --title test", "description": "Create PR"})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.pr_recorder import PrRecorder
        PrRecorder(hook_input).run()
        mock_session.update_session.assert_called_once()

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

        with patch("workflow.handlers.pr_recorder.SessionState") as MockSession:
            mock_session = MagicMock()
            mock_session.story_id = "SK-TEST"
            MockSession.return_value = mock_session
            from workflow.handlers.pr_recorder import PrRecorder
            PrRecorder(hook_input).run()
            mock_session.update_session.assert_not_called()

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
    def test_initialize_state_preserves_sessions(self, mock_cfg):
        """initialize_state preserves sessions dict."""
        mock_store = MagicMock()
        mock_store.load.return_value = {
            "sessions": {"SK-001": {"phase": {"current": "code"}}},
            "workflow_active": True,
        }
        with patch("workflow.initialize_state.StateStore", return_value=mock_store):
            from workflow.initialize_state import initialize_state
            data = make_user_prompt_input("test")
            hook_input = UserPromptSubmitInput.model_validate(data)
            initialize_state(hook_input)
        saved = mock_store.save.call_args[0][0]
        assert "sessions" in saved
        assert "SK-001" in saved["sessions"]
        assert saved["workflow_active"] is True


# ─── RecordCompletion ───────────────────────────────────────────────────────


class TestRecordCompletion:
    @patch("workflow.handlers.record_done.SessionState")
    @patch("workflow.handlers.record_done.check_workflow_gate", return_value=True)
    def test_done_status_sets_completed(self, mock_gate, MockSession):
        """Recording 'Done' status sets control.status to completed."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        MockSession.return_value = mock_session

        data = make_post_tool_input("Skill", {"skill": "log", "args": "SK-001 Done"})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.record_done import RecordCompletion
        RecordCompletion(hook_input).run()
        mock_session.update_session.assert_called_once()
