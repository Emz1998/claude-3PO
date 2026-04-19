"""Tests for the clarify auto-phase end-to-end behavior.

Covers initializer kickoff (clear vs. vague vs. --skip-clarify), the
PostToolUse hook resume loop on AskUserQuestion answers, the max_iterations
ceiling enforced by PhaseGuard, and progression to /explore on `clear`.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from utils.initializer import initialize
from lib.state_store import StateStore
from handlers.guardrails import phase_guard


SESSION_ID = "clarify-sess"


def _new_state(tmp_path: Path) -> tuple[Path, StateStore]:
    state_path = tmp_path / "state.json"
    store = StateStore(state_path)
    return state_path, store


def _clarify_phase(store: StateStore) -> dict | None:
    return store.build.get_clarify_phase()


# ═══════════════════════════════════════════════════════════════════
# Initializer — clarity check kickoff
# ═══════════════════════════════════════════════════════════════════


class TestInitializerClarifyKickoff:
    @patch("utils.initializer.clarity_check.run_initial")
    def test_clear_verdict_marks_clarify_skipped(self, mock_run, tmp_path):
        mock_run.return_value = ("sess_x", "clear")
        state_path, store = _new_state(tmp_path)
        initialize("build", SESSION_ID, "add /logout endpoint", state_path)

        phase = _clarify_phase(store)
        assert phase is not None
        assert phase["status"] == "skipped"
        assert "headless_session_id" not in phase
        assert "iteration_count" not in phase

    @patch("utils.initializer.clarity_check.run_initial")
    def test_vague_verdict_seeds_in_progress_with_session(self, mock_run, tmp_path):
        mock_run.return_value = ("sess_x", "vague")
        state_path, store = _new_state(tmp_path)
        initialize("build", SESSION_ID, "do the thing", state_path)

        phase = _clarify_phase(store)
        assert phase is not None
        assert phase["status"] == "in_progress"
        assert phase["headless_session_id"] == "sess_x"
        assert phase["iteration_count"] == 0

    @patch("utils.initializer.clarity_check.run_initial")
    def test_skip_clarify_flag_bypasses_check(self, mock_run, tmp_path):
        state_path, store = _new_state(tmp_path)
        initialize("build", SESSION_ID, "--skip-clarify anything", state_path)

        mock_run.assert_not_called()
        phase = _clarify_phase(store)
        assert phase is not None
        assert phase["status"] == "skipped"

    @patch("utils.initializer.clarity_check.run_initial")
    def test_implement_workflow_does_not_run_clarity(self, mock_run, tmp_path):
        state_path, store = _new_state(tmp_path)
        initialize("implement", SESSION_ID, "SK-001 something", state_path)

        mock_run.assert_not_called()
        assert _clarify_phase(store) is None


# ═══════════════════════════════════════════════════════════════════
# PostToolUse — resume on AskUserQuestion
# ═══════════════════════════════════════════════════════════════════


class TestClarifyResumeOnAskUserQuestion:
    """Each AskUserQuestion completion resumes the headless session and
    increments iteration_count. A 'clear' verdict completes the phase."""

    def _seed_in_progress(self, tmp_path):
        state_path, store = _new_state(tmp_path)
        with patch("utils.initializer.clarity_check.run_initial") as mr:
            mr.return_value = ("sess_x", "vague")
            initialize("build", SESSION_ID, "do the thing", state_path)
        return state_path, store

    @patch("utils.hooks.post_tool_use.clarity_check.run_resume")
    def test_resume_increments_iteration(self, mock_resume, tmp_path):
        from utils.hooks import post_tool_use

        mock_resume.return_value = "vague"
        state_path, store = self._seed_in_progress(tmp_path)

        hook_input = {
            "session_id": SESSION_ID,
            "tool_name": "AskUserQuestion",
            "tool_input": {"questions": [{"question": "?"}]},
            "tool_response": {"answers": {"?": "an answer"}},
        }
        post_tool_use.handle_clarify_resume(hook_input, store)

        phase = _clarify_phase(store)
        assert phase["iteration_count"] == 1
        assert phase["status"] == "in_progress"

    @patch("utils.hooks.post_tool_use.clarity_check.run_resume")
    def test_resume_clear_completes_phase(self, mock_resume, tmp_path):
        from utils.hooks import post_tool_use

        mock_resume.return_value = "clear"
        state_path, store = self._seed_in_progress(tmp_path)

        hook_input = {
            "session_id": SESSION_ID,
            "tool_name": "AskUserQuestion",
            "tool_input": {"questions": [{"question": "?"}]},
            "tool_response": {"answers": {"?": "good answer"}},
        }
        post_tool_use.handle_clarify_resume(hook_input, store)

        phase = _clarify_phase(store)
        assert phase["status"] == "completed"

    @patch("utils.hooks.post_tool_use.clarity_check.run_resume")
    def test_resume_uses_persisted_session_id(self, mock_resume, tmp_path):
        from utils.hooks import post_tool_use

        mock_resume.return_value = "vague"
        state_path, store = self._seed_in_progress(tmp_path)

        hook_input = {
            "session_id": SESSION_ID,
            "tool_name": "AskUserQuestion",
            "tool_input": {"questions": [{"question": "Q?"}]},
            "tool_response": {"answers": {"Q?": "A!"}},
        }
        post_tool_use.handle_clarify_resume(hook_input, store)

        called_session = mock_resume.call_args.args[0]
        assert called_session == "sess_x"

    @patch("utils.hooks.post_tool_use.clarity_check.run_resume")
    def test_no_resume_when_not_in_clarify(self, mock_resume, tmp_path):
        from utils.hooks import post_tool_use

        state_path, store = _new_state(tmp_path)
        # Set workflow to build with a different active phase (no clarify).
        store.reinitialize({
            "session_id": SESSION_ID,
            "workflow_active": True,
            "workflow_type": "build",
            "phases": [{"name": "explore", "status": "in_progress"}],
        })
        hook_input = {
            "session_id": SESSION_ID,
            "tool_name": "AskUserQuestion",
            "tool_input": {"questions": [{"question": "?"}]},
            "tool_response": {"answers": {"?": "a"}},
        }
        post_tool_use.handle_clarify_resume(hook_input, store)
        mock_resume.assert_not_called()


# ═══════════════════════════════════════════════════════════════════
# PhaseGuard — max_iterations safety ceiling
# ═══════════════════════════════════════════════════════════════════


class TestClarifyMaxIterations:
    def test_blocks_ask_user_question_at_ceiling(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("clarify")
        state.build.set_clarify_session("sess_x")
        max_iter = config.clarify_max_iterations
        for _ in range(max_iter):
            state.build.bump_clarify_iteration()
        from helpers import make_hook_input

        hook = make_hook_input(
            "AskUserQuestion",
            {"questions": [{"question": "?"}]},
        )
        decision, msg = phase_guard(hook, config, state)
        assert decision == "block"
        assert "max" in msg.lower() and "clarify" in msg.lower()

    def test_allows_ask_user_question_below_ceiling(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("clarify")
        state.build.set_clarify_session("sess_x")
        from helpers import make_hook_input

        hook = make_hook_input(
            "AskUserQuestion",
            {"questions": [{"question": "?"}]},
        )
        decision, _ = phase_guard(hook, config, state)
        assert decision == "allow"


# ═══════════════════════════════════════════════════════════════════
# Auto-advance — clarify completion advances to /explore
# ═══════════════════════════════════════════════════════════════════


class TestClarifyAdvancesToExplore:
    def test_completed_clarify_auto_advances(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("clarify")
        state.set_phase_completed("clarify")
        from utils.resolver import resolve

        resolve(config, state)
        # Next phase after clarify is explore (an agent phase, not auto, so
        # auto_start_next won't open it — the user must invoke /explore).
        # But clarify itself must remain completed.
        assert state.is_phase_completed("clarify")

    def test_skipped_clarify_does_not_block_explore(self, config, state):
        from helpers import make_hook_input

        state.set("workflow_type", "build")
        # Simulate initializer marking clarify skipped.
        def _seed(d):
            d.setdefault("phases", []).append({"name": "clarify", "status": "skipped"})
        state.update(_seed)

        hook = make_hook_input("Skill", {"skill": "explore"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "allow"
