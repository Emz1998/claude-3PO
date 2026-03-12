"""Tests for guards — CodingPhaseGuard, PreCodingPhaseGuard, PlanReviewPhaseGuard, StopGuard."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from workflow.models.hook_input import PreToolUseInput, StopInput
from helpers import make_pre_tool_input, make_stop_input


# ─── CodingPhaseGuard ────────────────────────────────────────────────────────


class TestCodingPhaseGuard:
    def _make_agent_input(self, subagent_type: str):
        """Build PreToolUseInput for an Agent tool invocation."""
        return PreToolUseInput.model_validate({
            "session_id": "test",
            "transcript_path": "/tmp/t.jsonl",
            "cwd": "/tmp",
            "permission_mode": "default",
            "hook_event_name": "PreToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": subagent_type, "args": ""},
            "tool_use_id": "toolu_1",
        })

    @patch("workflow.guards.code_phase.check_workflow_gate", return_value=True)
    @patch("workflow.guards.code_phase.cfg")
    @patch("workflow.guards.code_phase.SessionState")
    def test_valid_transition_passes(self, MockSession, mock_cfg, mock_gate):
        """Valid transition does not block."""
        mock_cfg.side_effect = lambda k: {
            "agents.test": ["TestEngineer"],
            "agents.code": ["CodeReviewer"],
        }.get(k)

        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = {
            "phase": {"recent_agent": None},
            "TDD": False,
        }
        MockSession.return_value = mock_session

        from workflow.guards.code_phase import CodingPhaseGuard

        mock_hook_input = MagicMock()
        mock_hook_input.tool_input.subagent_type = "CodeReviewer"

        with patch("workflow.guards.code_phase.validate_order", return_value=(True, "")):
            guard = CodingPhaseGuard(mock_hook_input)
            guard._session = mock_session
            guard.CODE_AGENTS = ["CodeReviewer"]
            guard.TEST_AGENTS = ["TestEngineer"]
            guard.run()

    @patch("workflow.guards.code_phase.check_workflow_gate", return_value=False)
    @patch("workflow.guards.code_phase.cfg")
    @patch("workflow.guards.code_phase.SessionState")
    def test_inactive_workflow_skips(self, MockSession, mock_cfg, mock_gate):
        """Inactive workflow skips guard entirely."""
        mock_cfg.side_effect = lambda k: {
            "agents.test": ["TestEngineer"],
            "agents.code": ["CodeReviewer"],
        }.get(k)
        MockSession.return_value = MagicMock()

        from workflow.guards.code_phase import CodingPhaseGuard

        hook_input = self._make_agent_input("CodeReviewer")
        guard = CodingPhaseGuard(hook_input)
        guard.run()

    def test_resolve_agents_with_tdd(self):
        """With TDD=True, resolve_agents_list returns test + code agents."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = {"TDD": True, "phase": {"recent_agent": None}}

        with patch("workflow.guards.code_phase.cfg") as mock_cfg, \
             patch("workflow.guards.code_phase.SessionState", return_value=mock_session):
            mock_cfg.side_effect = lambda k: {
                "agents.test": ["TestEngineer"],
                "agents.code": ["CodeReviewer"],
            }.get(k)

            from workflow.guards.code_phase import CodingPhaseGuard
            hook_input = self._make_agent_input("TestEngineer")
            guard = CodingPhaseGuard(hook_input)
            guard._session = mock_session
            guard.TEST_AGENTS = ["TestEngineer"]
            guard.CODE_AGENTS = ["CodeReviewer"]
            result = guard.resolve_agents_list()
            assert result == ["TestEngineer", "CodeReviewer"]


# ─── PreCodingPhaseGuard ─────────────────────────────────────────────────────


class TestPreCodingPhaseGuard:
    @patch("workflow.guards.pre_coding_phase.check_workflow_gate", return_value=True)
    @patch("workflow.guards.pre_coding_phase.cfg")
    @patch("workflow.guards.pre_coding_phase.SessionState")
    def test_plan_mode_valid(self, MockSession, mock_cfg, mock_gate):
        """In plan mode with valid transition, does not block."""
        mock_cfg.side_effect = lambda k: {
            "agents.pre_coding": ["Explore", "Plan", "PlanReviewer"],
        }.get(k)
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = {"phase": {"recent_agent": None}}
        MockSession.return_value = mock_session

        from workflow.guards.pre_coding_phase import PreCodingPhaseGuard

        data = make_pre_tool_input("Agent", {"description": "explore", "prompt": "explore", "subagent_type": "Explore"}, permission_mode="plan")
        hook_input = PreToolUseInput.model_validate(data)

        with patch("workflow.guards.pre_coding_phase.validate_order", return_value=(True, "")):
            guard = PreCodingPhaseGuard(hook_input)
            guard._session = mock_session
            guard.AGENTS = ["Explore", "Plan", "PlanReviewer"]
            guard.run()

    @patch("workflow.guards.pre_coding_phase.check_workflow_gate", return_value=True)
    @patch("workflow.guards.pre_coding_phase.cfg")
    @patch("workflow.guards.pre_coding_phase.SessionState")
    def test_non_plan_mode_skips(self, MockSession, mock_cfg, mock_gate):
        """Non-plan permission mode skips guard."""
        mock_cfg.side_effect = lambda k: {
            "agents.pre_coding": ["Explore", "Plan"],
        }.get(k)
        MockSession.return_value = MagicMock()

        from workflow.guards.pre_coding_phase import PreCodingPhaseGuard

        data = make_pre_tool_input("Skill", {"skill": "Explore", "args": ""}, permission_mode="default")
        hook_input = PreToolUseInput.model_validate(data)
        guard = PreCodingPhaseGuard(hook_input)
        guard.run()  # Should not block


# ─── PlanReviewPhaseGuard ────────────────────────────────────────────────────


class TestPlanReviewPhaseGuard:
    def test_edit_correct_path_passes(self):
        """Edit tool with correct plan file path passes."""
        from workflow.guards.pre_coding_phase import PlanReviewPhaseGuard

        data = make_pre_tool_input(
            "Edit",
            {"file_path": "/plans/my-plan.md", "old_string": "a", "new_string": "b"},
        )
        hook_input = PreToolUseInput.model_validate(data)
        guard = PlanReviewPhaseGuard(
            plan_file_path="/plans/my-plan.md",
            hook_input=hook_input,
        )
        # Should not block
        guard.run()

    def test_edit_wrong_path_blocks(self):
        """Edit tool with wrong file path blocks."""
        from workflow.guards.pre_coding_phase import PlanReviewPhaseGuard

        data = make_pre_tool_input(
            "Edit",
            {"file_path": "/other/file.md", "old_string": "a", "new_string": "b"},
        )
        hook_input = PreToolUseInput.model_validate(data)
        guard = PlanReviewPhaseGuard(
            plan_file_path="/plans/my-plan.md",
            hook_input=hook_input,
        )
        with pytest.raises(SystemExit) as exc:
            guard.run()
        assert exc.value.code == 2

    def test_non_edit_skips(self):
        """Non-Edit tool skips guard."""
        from workflow.guards.pre_coding_phase import PlanReviewPhaseGuard

        data = make_pre_tool_input("Skill", {"skill": "plan", "args": ""})
        hook_input = PreToolUseInput.model_validate(data)
        guard = PlanReviewPhaseGuard(
            plan_file_path="/plans/my-plan.md",
            hook_input=hook_input,
        )
        guard.run()  # Should not block


# ─── StopGuard ───────────────────────────────────────────────────────────────


class TestStopGuard:
    @patch("workflow.guards.stop_guard.check_workflow_gate", return_value=False)
    def test_inactive_workflow_skips(self, mock_gate):
        """Inactive workflow allows stop."""
        from workflow.guards.stop_guard import StopGuard

        data = make_stop_input()
        hook_input = StopInput.model_validate(data)
        guard = StopGuard(hook_input)
        guard.run()  # Should not block

    @patch("workflow.guards.stop_guard.SessionState")
    @patch("workflow.guards.stop_guard.check_workflow_gate", return_value=True)
    def test_completed_and_pr_created_allows(self, mock_gate, MockSession):
        """Completed session + PR created allows stop."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = {
            "control": {"status": "completed"},
            "pr": {"created": True},
        }
        MockSession.return_value = mock_session

        from workflow.guards.stop_guard import StopGuard

        data = make_stop_input(session_id="test-session")
        hook_input = StopInput.model_validate(data)
        guard = StopGuard(hook_input)
        guard.run()  # Should not block

    @patch("workflow.guards.stop_guard.SessionState")
    @patch("workflow.guards.stop_guard.check_workflow_gate", return_value=True)
    def test_not_completed_blocks(self, mock_gate, MockSession):
        """Running session blocks stop."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = {
            "control": {"status": "running"},
            "pr": {"created": False},
        }
        MockSession.return_value = mock_session

        from workflow.guards.stop_guard import StopGuard

        data = make_stop_input(session_id="test-session")
        hook_input = StopInput.model_validate(data)
        guard = StopGuard(hook_input)
        with pytest.raises(SystemExit) as exc:
            guard.run()
        assert exc.value.code == 2

    @patch("workflow.guards.stop_guard.SessionState")
    @patch("workflow.guards.stop_guard.check_workflow_gate", return_value=True)
    def test_completed_but_no_pr_blocks(self, mock_gate, MockSession):
        """Completed but no PR blocks stop."""
        mock_session = MagicMock()
        mock_session.story_id = "SK-TEST"
        mock_session.get_session.return_value = {
            "control": {"status": "completed"},
            "pr": {"created": False},
        }
        MockSession.return_value = mock_session

        from workflow.guards.stop_guard import StopGuard

        data = make_stop_input(session_id="test-session")
        hook_input = StopInput.model_validate(data)
        guard = StopGuard(hook_input)
        with pytest.raises(SystemExit) as exc:
            guard.run()
        assert exc.value.code == 2
