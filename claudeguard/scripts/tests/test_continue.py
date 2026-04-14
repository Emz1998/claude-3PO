"""Tests for /continue skill — force-completes the current phase and proceeds.

Note: /continue does not handle plan-review. Use /plan-approved instead.
"""

import pytest
from utils.state_store import StateStore
from utils.validators import is_phase_allowed
from helpers import make_hook_input


class TestContinueForceCompletes:
    """/continue force-completes any in-progress phase (except plan-review)."""

    def test_continue_force_completes_code_review(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("code-review")
        state.add_code_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_code_review_status("Fail")

        hook = make_hook_input("Skill", {"skill": "continue"})
        ok, _ = is_phase_allowed(hook, config, state)
        assert ok is True
        assert state.is_phase_completed("code-review")

    def test_continue_force_completes_test_review(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("test-review")
        state.add_test_review("Fail")

        hook = make_hook_input("Skill", {"skill": "continue"})
        ok, _ = is_phase_allowed(hook, config, state)
        assert ok is True
        assert state.is_phase_completed("test-review")

    def test_continue_force_completes_non_review_phase(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("write-code")

        hook = make_hook_input("Skill", {"skill": "continue"})
        ok, _ = is_phase_allowed(hook, config, state)
        assert ok is True
        assert state.is_phase_completed("write-code")


class TestContinueAfterCompleted:
    """Phase already completed — /continue auto-starts next."""

    def test_continue_after_code_review_passed(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("code-review")
        state.add_code_review({"confidence_score": 95, "quality_score": 95})
        state.set_last_code_review_status("Pass")
        state.complete_phase("code-review")

        hook = make_hook_input("Skill", {"skill": "continue"})
        ok, _ = is_phase_allowed(hook, config, state)
        assert ok is True


class TestContinueBlocked:
    """/continue blocked for plan-review and when no phases exist."""

    def test_blocked_for_plan_review(self, config, state):
        """/continue is blocked for plan-review — use /plan-approved instead."""
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 95, "quality_score": 95})
        state.set_last_plan_review_status("Pass")
        state.complete_phase("plan-review")

        hook = make_hook_input("Skill", {"skill": "continue"})
        with pytest.raises(ValueError, match="plan-approved"):
            is_phase_allowed(hook, config, state)

    def test_blocked_when_no_phases(self, config, state):
        hook = make_hook_input("Skill", {"skill": "continue"})
        with pytest.raises(ValueError):
            is_phase_allowed(hook, config, state)
