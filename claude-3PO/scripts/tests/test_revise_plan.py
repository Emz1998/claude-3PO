"""Tests for /revise-plan skill and plan_revised: null/false/true state."""

import pytest
from models.state import Agent
from guardrails import agent_guard
from helpers import make_hook_input, invoke_phase_guard as phase_guard


# ===================================================================
# plan_revised: null / false / true semantics
# ===================================================================


class TestPlanRevisedNullState:
    """plan_revised=None means fresh plan, never reviewed."""

    def test_default_is_none(self, state):
        assert state.plan_revised is None

    def test_first_plan_review_allowed_when_none(self, config, state):
        """PlanReview agent allowed on first invocation (plan_revised=None)."""
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        hook = make_hook_input("Agent", {"subagent_type": "PlanReview"})
        decision, _ = agent_guard(hook, config, state)
        assert decision == "allow"

    def test_plan_review_blocked_when_false(self, config, state):
        """PlanReview blocked when plan_revised=False (needs edit first)."""
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_plan_review_status("Fail")
        state.set_plan_revised(False)
        hook = make_hook_input("Agent", {"subagent_type": "PlanReview"})
        decision, msg = agent_guard(hook, config, state)
        assert decision == "block"
        assert "revised" in msg.lower()

    def test_plan_review_allowed_when_true(self, config, state):
        """PlanReview allowed after plan edited (plan_revised=True)."""
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_plan_review_status("Fail")
        state.set_plan_revised(True)
        hook = make_hook_input("Agent", {"subagent_type": "PlanReview"})
        decision, _ = agent_guard(hook, config, state)
        assert decision == "allow"


# ===================================================================
# /revise-plan — reopen plan-review after pass or exhaustion
# ===================================================================


class TestRevisePlan:
    def test_reopens_plan_review_after_checkpoint(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 95, "quality_score": 95})
        state.set_last_plan_review_status("Pass")
        state.set_phase_completed("plan-review")

        hook = make_hook_input("Skill", {"skill": "revise-plan"})
        decision, msg = phase_guard(hook, config, state)
        assert decision == "allow"

        # Phase should be back to in_progress
        assert state.get_phase_status("plan-review") == "in_progress"
        # plan_revised should be False (needs edit before re-review)
        assert state.plan_revised is False
        # Reviews should be reset for fresh cycle
        assert state.plan_review_count == 0

    def test_allowed_after_exhaustion(self, config, state):
        """3 fails -> /revise-plan works, reviews reset."""
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_plan_review_status("Fail")
        state.add_plan_review({"confidence_score": 60, "quality_score": 60})
        state.set_last_plan_review_status("Fail")
        state.add_plan_review({"confidence_score": 70, "quality_score": 70})
        state.set_last_plan_review_status("Fail")

        hook = make_hook_input("Skill", {"skill": "revise-plan"})
        decision, msg = phase_guard(hook, config, state)
        assert decision == "allow"

        # Phase should be back to in_progress
        assert state.get_phase_status("plan-review") == "in_progress"
        # Reviews reset for fresh cycle
        assert state.plan_review_count == 0
        assert state.plan_revised is False

    def test_blocked_when_in_progress_not_exhausted(self, config, state):
        """Only 1 fail — can't revise yet (not at checkpoint or exhaustion)."""
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_plan_review_status("Fail")

        hook = make_hook_input("Skill", {"skill": "revise-plan"})
        decision, msg = phase_guard(hook, config, state)
        assert decision == "block"

    def test_blocked_in_wrong_phase(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("explore")

        hook = make_hook_input("Skill", {"skill": "revise-plan"})
        decision, msg = phase_guard(hook, config, state)
        assert decision == "block"
        assert "plan-review" in msg

    def test_blocked_when_plan_review_not_current(self, config, state):
        """Can't revise-plan if we've already moved past plan-review."""
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.set_phase_completed("plan-review")
        state.add_phase("create-tasks")
        state.set_phase_completed("create-tasks")
        state.add_phase("install-deps")

        hook = make_hook_input("Skill", {"skill": "revise-plan"})
        decision, msg = phase_guard(hook, config, state)
        assert decision == "block"
        assert "plan-review" in msg

    def test_edit_then_plan_review_allowed(self, config, state):
        """After /revise-plan, editing plan sets plan_revised=True, then PlanReview allowed."""
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 95, "quality_score": 95})
        state.set_last_plan_review_status("Pass")
        state.set_phase_completed("plan-review")

        # /revise-plan
        hook = make_hook_input("Skill", {"skill": "revise-plan"})
        phase_guard(hook, config, state)

        # PlanReview blocked before edit
        hook = make_hook_input("Agent", {"subagent_type": "PlanReview"})
        decision, msg = agent_guard(hook, config, state)
        assert decision == "block"
        assert "revised" in msg.lower()

        # Simulate edit
        state.set_plan_revised(True)

        # PlanReview now allowed
        decision, _ = agent_guard(hook, config, state)
        assert decision == "allow"
