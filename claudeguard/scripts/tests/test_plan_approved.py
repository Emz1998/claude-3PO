"""Tests for /plan-approved skill — user approves plan and proceeds."""

import pytest
from utils.state_store import StateStore
from utils.validators import is_phase_allowed
from helpers import make_hook_input


class TestPlanApprovedAfterCheckpoint:
    """/plan-approved after plan-review passed (checkpoint)."""

    def test_plan_approved_after_checkpoint(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 95, "quality_score": 95})
        state.set_last_plan_review_status("Pass")
        state.complete_phase("plan-review")

        hook = make_hook_input("Skill", {"skill": "plan-approved"})
        ok, msg = is_phase_allowed(hook, config, state)
        assert ok is True
        assert "Plan approved" in msg

    def test_plan_approved_auto_starts_next_phase(self, config, state):
        """After /plan-approved, the next auto-phase (create-tasks) starts."""
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 95, "quality_score": 95})
        state.set_last_plan_review_status("Pass")
        state.complete_phase("plan-review")

        hook = make_hook_input("Skill", {"skill": "plan-approved"})
        is_phase_allowed(hook, config, state)

        # create-tasks is the auto-phase after plan-review
        assert state.current_phase == "create-tasks"
        assert state.get_phase_status("create-tasks") == "in_progress"


class TestPlanApprovedAfterExhaustion:
    """/plan-approved after 3 failed reviews (exhaustion)."""

    def test_plan_approved_after_exhaustion(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_plan_review_status("Fail")
        state.add_plan_review({"confidence_score": 60, "quality_score": 60})
        state.set_last_plan_review_status("Fail")
        state.add_plan_review({"confidence_score": 70, "quality_score": 70})
        state.set_last_plan_review_status("Fail")

        hook = make_hook_input("Skill", {"skill": "plan-approved"})
        ok, msg = is_phase_allowed(hook, config, state)
        assert ok is True
        assert state.is_phase_completed("plan-review")
        assert "exhaustion" in msg


class TestPlanApprovedBlocked:
    """Cases where /plan-approved should be blocked."""

    def test_blocked_not_plan_review(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("code-review")

        hook = make_hook_input("Skill", {"skill": "plan-approved"})
        with pytest.raises(ValueError, match="only.*during plan-review"):
            is_phase_allowed(hook, config, state)

    def test_blocked_in_progress_not_exhausted(self, config, state):
        """Only 1 fail, can't approve yet."""
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_plan_review_status("Fail")

        hook = make_hook_input("Skill", {"skill": "plan-approved"})
        with pytest.raises(ValueError, match="checkpoint.*or exhausted"):
            is_phase_allowed(hook, config, state)

    def test_blocked_no_reviews_yet(self, config, state):
        """Fresh plan-review with no reviews — can't approve."""
        state.set("workflow_type", "build")
        state.add_phase("plan-review")

        hook = make_hook_input("Skill", {"skill": "plan-approved"})
        with pytest.raises(ValueError, match="checkpoint.*or exhausted"):
            is_phase_allowed(hook, config, state)
