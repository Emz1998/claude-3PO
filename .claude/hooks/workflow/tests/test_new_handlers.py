"""Tests for new handlers — ReviewTrigger, SessionLogger, SimplifyTrigger, CiCheckHandler, CleanupTrigger."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from workflow.models.hook_input import PostToolUseInput, PreToolUseInput, UserPromptSubmitInput
from helpers import make_post_tool_input, make_pre_tool_input, make_user_prompt_input


# ─── ReviewTrigger ───────────────────────────────────────────────────────────


class TestReviewTrigger:
    """Tests for review_trigger.py — creates PR review session from /review prompt."""

    @patch("workflow.handlers.review_trigger.SessionState")
    @patch("workflow.handlers.review_trigger.check_workflow_gate", return_value=True)
    def test_creates_pr_review_session(self, mock_gate, MockSession):
        """/review 42 → creates sessions['PR-42']."""
        mock_session = MagicMock()
        mock_session.story_id = None  # PR reviews don't need STORY_ID
        MockSession.return_value = mock_session

        data = make_user_prompt_input("/review 42")
        hook_input = UserPromptSubmitInput.model_validate(data)

        from workflow.handlers.review_trigger import ReviewTrigger
        ReviewTrigger(hook_input).run()
        mock_session.create_session.assert_called_once()
        call_args = mock_session.create_session.call_args
        assert call_args[0][0] == "PR-42"

    @patch("workflow.handlers.review_trigger.check_workflow_gate", return_value=True)
    def test_ignores_non_review_prompts(self, mock_gate):
        """'hello' → no-op."""
        data = make_user_prompt_input("hello")
        hook_input = UserPromptSubmitInput.model_validate(data)

        from workflow.handlers.review_trigger import ReviewTrigger
        ReviewTrigger(hook_input).run()  # Should not raise

    @patch("workflow.handlers.review_trigger.SessionState")
    @patch("workflow.handlers.review_trigger.check_workflow_gate", return_value=True)
    def test_session_has_pr_review_type(self, mock_gate, MockSession):
        """Created session has workflow_type='pr-review'."""
        from workflow.session_state import SessionState as RealSessionState

        mock_session = MagicMock()
        MockSession.return_value = mock_session
        MockSession.default_pr_review_session = RealSessionState.default_pr_review_session

        data = make_user_prompt_input("/review 42")
        hook_input = UserPromptSubmitInput.model_validate(data)

        from workflow.handlers.review_trigger import ReviewTrigger
        ReviewTrigger(hook_input).run()
        call_args = mock_session.create_session.call_args
        session_data = call_args[0][1]
        assert session_data["workflow_type"] == "pr-review"


# ─── SessionLogger ───────────────────────────────────────────────────────────


class TestSessionLogger:
    """Tests for session_logger.py — appends JSONL log entries per tool use."""

    @patch("workflow.handlers.session_logger.SessionState")
    @patch("workflow.handlers.session_logger.check_workflow_gate", return_value=True)
    def test_appends_jsonl_entry(self, mock_gate, MockSession, tmp_path):
        """Log file should have an entry after tool use."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = {"phase": {"current": "code"}}
        MockSession.return_value = mock_session

        log_file = tmp_path / "log.jsonl"

        data = make_post_tool_input("Bash", {"command": "ls", "description": "List"})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.session_logger import SessionLogger
        with patch("workflow.handlers.session_logger.get_log_path", return_value=log_file):
            SessionLogger(hook_input).run()

        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1

    @patch("workflow.handlers.session_logger.SessionState")
    @patch("workflow.handlers.session_logger.check_workflow_gate", return_value=True)
    def test_entry_has_required_fields(self, mock_gate, MockSession, tmp_path):
        """Log entry should have ts, session, event, phase."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = {"phase": {"current": "code"}}
        MockSession.return_value = mock_session

        log_file = tmp_path / "log.jsonl"

        data = make_post_tool_input("Bash", {"command": "ls", "description": "List"})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.session_logger import SessionLogger
        with patch("workflow.handlers.session_logger.get_log_path", return_value=log_file):
            SessionLogger(hook_input).run()

        entry = json.loads(log_file.read_text().strip())
        assert "ts" in entry
        assert entry["session"] == "SK-TEST"
        assert entry["event"] == "Bash"
        assert entry["phase"] == "code"

    @patch("workflow.handlers.session_logger.SessionState")
    @patch("workflow.handlers.session_logger.check_workflow_gate", return_value=True)
    def test_no_story_id_is_noop(self, mock_gate, MockSession, tmp_path):
        """No STORY_ID → no file written."""
        mock_session = MagicMock()
        mock_session.story_id = None
        MockSession.return_value = mock_session

        log_file = tmp_path / "log.jsonl"

        data = make_post_tool_input("Bash", {"command": "ls", "description": "List"})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.session_logger import SessionLogger
        with patch("workflow.handlers.session_logger.get_log_path", return_value=log_file):
            SessionLogger(hook_input).run()

        assert not log_file.exists()


# ─── SimplifyTrigger ─────────────────────────────────────────────────────────


class TestSimplifyTrigger:
    """Tests for simplify_trigger.py — injects /simplify on new file creation during code phase."""

    @patch("workflow.handlers.simplify_trigger.SessionState")
    @patch("workflow.handlers.simplify_trigger.check_workflow_gate", return_value=True)
    def test_injects_simplify_on_new_file_in_code_phase(self, mock_gate, MockSession):
        """Write tool in code phase → systemMessage output."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = {"phase": {"current": "code"}}
        MockSession.return_value = mock_session

        data = make_post_tool_input("Write", {"file_path": "/src/new_file.py", "content": "print('hi')"})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.simplify_trigger import SimplifyTrigger
        with pytest.raises(SystemExit) as exc:
            SimplifyTrigger(hook_input).run()
        assert exc.value.code == 0

    @patch("workflow.handlers.simplify_trigger.SessionState")
    @patch("workflow.handlers.simplify_trigger.check_workflow_gate", return_value=True)
    def test_skips_non_code_phase(self, mock_gate, MockSession):
        """Write tool outside code phase → no output."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = {"phase": {"current": "pre-coding"}}
        MockSession.return_value = mock_session

        data = make_post_tool_input("Write", {"file_path": "/src/new_file.py", "content": "print('hi')"})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.simplify_trigger import SimplifyTrigger
        SimplifyTrigger(hook_input).run()  # Should not raise

    @patch("workflow.handlers.simplify_trigger.SessionState")
    @patch("workflow.handlers.simplify_trigger.check_workflow_gate", return_value=True)
    def test_skips_edit_tool(self, mock_gate, MockSession):
        """Edit tool (existing file) → no output."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = {"phase": {"current": "code"}}
        MockSession.return_value = mock_session

        data = make_post_tool_input("Edit", {"file_path": "/src/file.py", "old_string": "a", "new_string": "b"})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.simplify_trigger import SimplifyTrigger
        SimplifyTrigger(hook_input).run()  # Should not raise


# ─── CiCheckHandler ─────────────────────────────────────────────────────────


class TestCiCheckHandler:
    """Tests for ci_check_handler.py — updates CI status after push."""

    def _make_session(self, ci_status="pending", ci_iteration=0, ci_escalate=False):
        return {
            "phase": {"current": "push"},
            "control": {"status": "running"},
            "pr": {"created": True, "number": 42},
            "ci": {"status": ci_status, "iteration_count": ci_iteration, "escalate_to_user": ci_escalate},
        }

    @patch("workflow.handlers.ci_check_handler.SessionState")
    @patch("workflow.handlers.ci_check_handler.check_workflow_gate", return_value=True)
    def test_updates_ci_status_on_pass(self, mock_gate, MockSession):
        """CI pass → session.ci.status = 'pass'."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session()
        MockSession.return_value = mock_session

        data = make_post_tool_input("Skill", {"skill": "push", "args": ""})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.ci_check_handler import CiCheckHandler
        with patch("workflow.handlers.ci_check_handler.poll_ci_status", return_value="pass"):
            CiCheckHandler(hook_input).run()
        mock_session.update_session.assert_called_once()

    @patch("workflow.handlers.ci_check_handler.SessionState")
    @patch("workflow.handlers.ci_check_handler.check_workflow_gate", return_value=True)
    def test_increments_iteration_on_fail(self, mock_gate, MockSession):
        """CI fail → iteration_count += 1."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(ci_iteration=0)
        MockSession.return_value = mock_session

        data = make_post_tool_input("Skill", {"skill": "push", "args": ""})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.ci_check_handler import CiCheckHandler
        with patch("workflow.handlers.ci_check_handler.poll_ci_status", return_value="fail"):
            CiCheckHandler(hook_input).run()
        mock_session.update_session.assert_called()

    @patch("workflow.handlers.ci_check_handler.SessionState")
    @patch("workflow.handlers.ci_check_handler.check_workflow_gate", return_value=True)
    @patch("workflow.handlers.ci_check_handler.cfg")
    def test_escalates_at_max_iterations(self, mock_cfg, mock_gate, MockSession):
        """CI fail at max iterations → escalate_to_user = True."""
        mock_cfg.return_value = 2
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(ci_iteration=2)
        MockSession.return_value = mock_session

        data = make_post_tool_input("Skill", {"skill": "push", "args": ""})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.ci_check_handler import CiCheckHandler
        with patch("workflow.handlers.ci_check_handler.poll_ci_status", return_value="fail"):
            CiCheckHandler(hook_input).run()
        mock_session.update_session.assert_called()

    @patch("workflow.handlers.ci_check_handler.check_workflow_gate", return_value=True)
    def test_ignores_non_push_skills(self, mock_gate):
        """/plan → no-op."""
        data = make_post_tool_input("Skill", {"skill": "plan", "args": ""})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.ci_check_handler import CiCheckHandler
        CiCheckHandler(hook_input).run()  # Should not raise


# ─── CleanupTrigger ──────────────────────────────────────────────────────────


class TestCleanupTrigger:
    """Tests for cleanup_trigger.py — removes worktree after CI green."""

    def _make_session(self, ci_status="pending"):
        return {
            "phase": {"current": "push"},
            "control": {"status": "running"},
            "pr": {"created": True, "number": 42},
            "ci": {"status": ci_status, "iteration_count": 0, "escalate_to_user": False},
        }

    @patch("workflow.handlers.cleanup_trigger.SessionState")
    @patch("workflow.handlers.cleanup_trigger.check_workflow_gate", return_value=True)
    def test_no_cleanup_when_ci_pending(self, mock_gate, MockSession):
        """ci.status != 'pass' → no-op."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(ci_status="pending")
        MockSession.return_value = mock_session

        data = make_post_tool_input("Skill", {"skill": "push", "args": ""})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.cleanup_trigger import CleanupTrigger
        with patch("workflow.handlers.cleanup_trigger.remove_worktree") as mock_remove:
            CleanupTrigger(hook_input).run()
            mock_remove.assert_not_called()

    @patch("workflow.handlers.cleanup_trigger.SessionState")
    @patch("workflow.handlers.cleanup_trigger.check_workflow_gate", return_value=True)
    def test_cleanup_after_ci_green(self, mock_gate, MockSession):
        """ci.status == 'pass' → subprocess called for worktree remove."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(ci_status="pass")
        MockSession.return_value = mock_session

        data = make_post_tool_input("Skill", {"skill": "push", "args": ""})
        hook_input = PostToolUseInput.model_validate(data)

        from workflow.handlers.cleanup_trigger import CleanupTrigger
        with patch("workflow.handlers.cleanup_trigger.remove_worktree") as mock_remove:
            CleanupTrigger(hook_input).run()
            mock_remove.assert_called_once()
