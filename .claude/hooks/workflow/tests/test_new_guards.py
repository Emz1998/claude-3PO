"""Tests for new guards — PhaseGuard, HoldChecker, BashGuard."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from workflow.models.hook_input import PreToolUseInput
from helpers import make_pre_tool_input


# ─── PhaseGuard ──────────────────────────────────────────────────────────────


class TestPhaseGuard:
    """Tests for phase_guard.py — validates workflow phase transitions."""

    def _make_session(self, phase_current="pre-coding", hold=False, blocked_until_phase=None):
        return {
            "phase": {"current": phase_current, "previous": None, "recent_agent": None},
            "control": {"status": "running", "hold": hold, "blocked_until_phase": blocked_until_phase},
            "pr": {"created": False, "number": None},
            "validation": {"decision_invoked": False, "confidence_score": 0, "quality_score": 0, "iteration_count": 0},
            "ci": {"status": "pending", "iteration_count": 0},
        }

    @patch("workflow.guards.phase_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.phase_guard.SessionState")
    def test_valid_transition_allows(self, MockSession, mock_gate):
        """pre-coding → code: should exit 0 (allow)."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(phase_current="pre-coding")
        MockSession.return_value = mock_session

        from workflow.guards.phase_guard import PhaseGuard
        guard = PhaseGuard(predecessor="pre-coding", current="code")
        guard.run()  # Should not raise

    @patch("workflow.guards.phase_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.phase_guard.SessionState")
    def test_invalid_transition_blocks(self, MockSession, mock_gate):
        """pre-coding → push: should exit 2 (block)."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(phase_current="code")
        MockSession.return_value = mock_session

        from workflow.guards.phase_guard import PhaseGuard
        guard = PhaseGuard(predecessor="pre-coding", current="code")
        with pytest.raises(SystemExit) as exc:
            guard.run()
        assert exc.value.code == 2

    @patch("workflow.guards.phase_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.phase_guard.SessionState")
    def test_hold_true_blocks(self, MockSession, mock_gate):
        """control.hold=True should exit 2 (block)."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(hold=True)
        MockSession.return_value = mock_session

        from workflow.guards.phase_guard import PhaseGuard
        guard = PhaseGuard(predecessor="pre-coding", current="code")
        with pytest.raises(SystemExit) as exc:
            guard.run()
        assert exc.value.code == 2

    @patch("workflow.guards.phase_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.phase_guard.SessionState")
    def test_blocked_until_phase_blocks(self, MockSession, mock_gate):
        """blocked_until_phase set should exit 2 (block)."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(blocked_until_phase="review")
        MockSession.return_value = mock_session

        from workflow.guards.phase_guard import PhaseGuard
        guard = PhaseGuard(predecessor="pre-coding", current="code")
        with pytest.raises(SystemExit) as exc:
            guard.run()
        assert exc.value.code == 2

    @patch("workflow.guards.phase_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.phase_guard.SessionState")
    def test_records_transition_on_success(self, MockSession, mock_gate):
        """Should update phase.previous on successful transition."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(phase_current="pre-coding")
        MockSession.return_value = mock_session

        from workflow.guards.phase_guard import PhaseGuard
        guard = PhaseGuard(predecessor="pre-coding", current="code")
        guard.run()
        mock_session.update_session.assert_called_once()

    @patch("workflow.guards.phase_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.phase_guard.SessionState")
    def test_no_story_id_is_noop(self, MockSession, mock_gate):
        """No STORY_ID → graceful no-op."""
        mock_session = MagicMock()
        mock_session.story_id = None
        MockSession.return_value = mock_session

        from workflow.guards.phase_guard import PhaseGuard
        guard = PhaseGuard(predecessor="pre-coding", current="code")
        guard.run()  # Should not raise


# ─── HoldChecker ─────────────────────────────────────────────────────────────


class TestHoldChecker:
    """Tests for hold_checker.py — blocks Agent/Skill when session is on hold."""

    def _make_session(self, hold=False, status="running"):
        return {
            "phase": {"current": "code", "previous": None, "recent_agent": None},
            "control": {"status": status, "hold": hold, "blocked_until_phase": None},
            "pr": {"created": False, "number": None},
            "validation": {"decision_invoked": False},
            "ci": {"status": "pending"},
        }

    @patch("workflow.guards.hold_checker.check_workflow_gate", return_value=True)
    @patch("workflow.guards.hold_checker.SessionState")
    def test_hold_true_blocks_agent(self, MockSession, mock_gate):
        """hold=True + Agent tool → exit 2."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(hold=True)
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Agent", {"description": "test", "prompt": "test", "subagent_type": "Explore"})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.hold_checker import HoldChecker
        with pytest.raises(SystemExit) as exc:
            HoldChecker(hook_input).run()
        assert exc.value.code == 2

    @patch("workflow.guards.hold_checker.check_workflow_gate", return_value=True)
    @patch("workflow.guards.hold_checker.SessionState")
    def test_hold_true_blocks_skill(self, MockSession, mock_gate):
        """hold=True + Skill tool → exit 2."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(hold=True)
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Skill", {"skill": "plan", "args": ""})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.hold_checker import HoldChecker
        with pytest.raises(SystemExit) as exc:
            HoldChecker(hook_input).run()
        assert exc.value.code == 2

    @patch("workflow.guards.hold_checker.check_workflow_gate", return_value=True)
    @patch("workflow.guards.hold_checker.SessionState")
    def test_hold_false_allows(self, MockSession, mock_gate):
        """hold=False → exit 0 (allow)."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(hold=False)
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Agent", {"description": "test", "prompt": "test", "subagent_type": "Explore"})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.hold_checker import HoldChecker
        HoldChecker(hook_input).run()  # Should not raise

    @patch("workflow.guards.hold_checker.check_workflow_gate", return_value=True)
    @patch("workflow.guards.hold_checker.SessionState")
    def test_aborted_status_blocks(self, MockSession, mock_gate):
        """status='aborted' → exit 2."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(status="aborted")
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Agent", {"description": "test", "prompt": "test", "subagent_type": "Explore"})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.hold_checker import HoldChecker
        with pytest.raises(SystemExit) as exc:
            HoldChecker(hook_input).run()
        assert exc.value.code == 2

    @patch("workflow.guards.hold_checker.check_workflow_gate", return_value=True)
    @patch("workflow.guards.hold_checker.SessionState")
    def test_no_story_id_allows(self, MockSession, mock_gate):
        """No STORY_ID → exit 0 (allow)."""
        mock_session = MagicMock()
        mock_session.story_id = None
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Agent", {"description": "test", "prompt": "test", "subagent_type": "Explore"})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.hold_checker import HoldChecker
        HoldChecker(hook_input).run()  # Should not raise


# ─── BashGuard ───────────────────────────────────────────────────────────────


class TestBashGuard:
    """Tests for bash_guard.py — restricts dangerous bash commands by phase."""

    def _make_session(self, phase_current="code"):
        return {
            "phase": {"current": phase_current, "previous": None, "recent_agent": None},
            "control": {"status": "running", "hold": False, "blocked_until_phase": None},
            "pr": {"created": False, "number": None},
            "validation": {"decision_invoked": False},
            "ci": {"status": "pending"},
        }

    @patch("workflow.guards.bash_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.bash_guard.SessionState")
    def test_gh_pr_create_blocked_outside_phase(self, MockSession, mock_gate):
        """gh pr create outside create-pr phase → exit 2."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(phase_current="code")
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Bash", {"command": "gh pr create --title test", "description": "Create PR"})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.bash_guard import BashGuard
        with pytest.raises(SystemExit) as exc:
            BashGuard(hook_input).run()
        assert exc.value.code == 2

    @patch("workflow.guards.bash_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.bash_guard.SessionState")
    def test_gh_pr_create_allowed_in_phase(self, MockSession, mock_gate):
        """gh pr create in create-pr phase → exit 0."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(phase_current="create-pr")
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Bash", {"command": "gh pr create --title test", "description": "Create PR"})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.bash_guard import BashGuard
        BashGuard(hook_input).run()  # Should not raise

    @patch("workflow.guards.bash_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.bash_guard.SessionState")
    def test_gh_pr_close_always_blocked(self, MockSession, mock_gate):
        """gh pr close → always exit 2."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(phase_current="create-pr")
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Bash", {"command": "gh pr close 42", "description": "Close PR"})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.bash_guard import BashGuard
        with pytest.raises(SystemExit) as exc:
            BashGuard(hook_input).run()
        assert exc.value.code == 2

    @patch("workflow.guards.bash_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.bash_guard.SessionState")
    def test_gh_pr_merge_always_blocked(self, MockSession, mock_gate):
        """gh pr merge → always exit 2."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(phase_current="create-pr")
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Bash", {"command": "gh pr merge 42", "description": "Merge PR"})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.bash_guard import BashGuard
        with pytest.raises(SystemExit) as exc:
            BashGuard(hook_input).run()
        assert exc.value.code == 2

    @patch("workflow.guards.bash_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.bash_guard.SessionState")
    def test_git_push_blocked_outside_phase(self, MockSession, mock_gate):
        """git push outside push phase → exit 2."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(phase_current="code")
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Bash", {"command": "git push origin main", "description": "Push"})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.bash_guard import BashGuard
        with pytest.raises(SystemExit) as exc:
            BashGuard(hook_input).run()
        assert exc.value.code == 2

    @patch("workflow.guards.bash_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.bash_guard.SessionState")
    def test_git_push_allowed_in_phase(self, MockSession, mock_gate):
        """git push in push phase → exit 0."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(phase_current="push")
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Bash", {"command": "git push origin main", "description": "Push"})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.bash_guard import BashGuard
        BashGuard(hook_input).run()  # Should not raise

    @patch("workflow.guards.bash_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.bash_guard.SessionState")
    def test_normal_bash_allowed(self, MockSession, mock_gate):
        """ls, echo, etc → exit 0."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = self._make_session(phase_current="code")
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Bash", {"command": "ls -la", "description": "List files"})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.bash_guard import BashGuard
        BashGuard(hook_input).run()  # Should not raise

    @patch("workflow.guards.bash_guard.check_workflow_gate", return_value=True)
    @patch("workflow.guards.bash_guard.SessionState")
    def test_no_story_id_allows_all(self, MockSession, mock_gate):
        """No STORY_ID → exit 0 (allow all)."""
        mock_session = MagicMock()
        mock_session.story_id = None
        MockSession.return_value = mock_session

        data = make_pre_tool_input("Bash", {"command": "gh pr create --title test", "description": "Create PR"})
        hook_input = PreToolUseInput.model_validate(data)

        from workflow.guards.bash_guard import BashGuard
        BashGuard(hook_input).run()  # Should not raise
