"""Tests for guards/review_guard.py (new unified version)."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow.guards import review_guard
from workflow.state_store import StateStore


def make_state(phase: str, **kwargs) -> dict:
    return {
        "workflow_active": True,
        "workflow_type": kwargs.get("workflow_type", "implement"),
        "phase": phase,
        "tdd": kwargs.get("tdd", True),
        "skip_explore": kwargs.get("skip_explore", False),
        "skip_research": kwargs.get("skip_research", False),
        "agents": kwargs.get("agents", []),
        "plan_review_iteration": kwargs.get("plan_review_iteration", 0),
        "plan_review_scores": kwargs.get("plan_review_scores", None),
        "plan_review_status": kwargs.get("plan_review_status", None),
        "story_id": kwargs.get("story_id", None),
        "test_review_result": kwargs.get("test_review_result", None),
        "validation_result": kwargs.get("validation_result", None),
    }


def write_state(tmp_state_file, state: dict) -> None:
    tmp_state_file.write_text(json.dumps(state))


def stop_hook(agent_type: str, msg: str = "Done.") -> dict:
    return {
        "hook_event_name": "SubagentStop",
        "agent_type": agent_type,
        "agent_id": "a1",
        "last_assistant_message": msg,
        "session_id": "s", "transcript_path": "t", "cwd": ".",
        "permission_mode": "default", "stop_hook_active": False,
        "agent_transcript_path": "x.jsonl",
    }


def running_agent(agent_type: str) -> dict:
    return {"agent_type": agent_type, "status": "running", "tool_use_id": "t1"}


# ---------------------------------------------------------------------------
# Explore / Research: mark completed, auto-advance
# ---------------------------------------------------------------------------

class TestExploreResearchCompletion:
    def test_explore_completion_marks_completed(self, tmp_state_file):
        agents = [running_agent("Explore"), running_agent("Explore"), running_agent("Explore"),
                  running_agent("Research"), running_agent("Research")]
        write_state(tmp_state_file, make_state("explore", agents=agents))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("Explore"), store)
        state = store.load()
        completed = [a for a in state["agents"] if a["agent_type"] == "Explore" and a["status"] == "completed"]
        assert len(completed) == 1

    def test_all_explore_done_advances_to_plan(self, tmp_state_file):
        agents = (
            [{"agent_type": "Explore", "status": "completed"}] * 2 +
            [running_agent("Explore")] +
            [{"agent_type": "Research", "status": "completed"}] * 2
        )
        write_state(tmp_state_file, make_state("explore", agents=agents))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("Explore"), store)
        state = store.load()
        assert state["phase"] == "plan"

    def test_partial_explore_does_not_advance(self, tmp_state_file):
        agents = [running_agent("Explore")]  # only 1 of 3
        write_state(tmp_state_file, make_state("explore", agents=agents))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("Explore"), store)
        state = store.load()
        assert state["phase"] == "explore"

    def test_skip_explore_only_needs_research(self, tmp_state_file):
        agents = [running_agent("Research"), {"agent_type": "Research", "status": "completed"}]
        state = make_state("explore", agents=agents, skip_explore=True)
        write_state(tmp_state_file, state)
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("Research"), store)
        state = store.load()
        assert state["phase"] == "plan"

    def test_skip_research_only_needs_explore(self, tmp_state_file):
        agents = (
            [{"agent_type": "Explore", "status": "completed"}] * 2 +
            [running_agent("Explore")]
        )
        state = make_state("explore", agents=agents, skip_research=True)
        write_state(tmp_state_file, state)
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("Explore"), store)
        state = store.load()
        assert state["phase"] == "plan"


# ---------------------------------------------------------------------------
# Plan: advance to write-plan
# ---------------------------------------------------------------------------

class TestPlanCompletion:
    def test_plan_stop_advances_to_write_plan(self, tmp_state_file):
        agents = [running_agent("Plan")]
        write_state(tmp_state_file, make_state("plan", agents=agents))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("Plan", "I have created the plan."), store)
        state = store.load()
        assert state["phase"] == "write-plan"


# ---------------------------------------------------------------------------
# PlanReview: parse scores, advance or iterate
# ---------------------------------------------------------------------------

class TestPlanReviewCompletion:
    def test_plan_review_approved_advances_to_approved(self, tmp_state_file):
        agents = [running_agent("PlanReview")]
        write_state(tmp_state_file, make_state("review", agents=agents))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("PlanReview", "Confidence score: 90, Quality score: 85"), store)
        state = store.load()
        assert state["phase"] == "approved"
        assert state["plan_review_status"] == "approved"

    def test_plan_review_failing_increments_iteration(self, tmp_state_file):
        agents = [running_agent("PlanReview")]
        write_state(tmp_state_file, make_state("review", agents=agents))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("PlanReview", "Confidence: 50, Quality: 45"), store)
        state = store.load()
        assert state["phase"] == "review"
        assert state["plan_review_iteration"] == 1
        assert state["plan_review_status"] == "revision_needed"

    def test_plan_review_max_iterations_sets_failed(self, tmp_state_file):
        agents = [running_agent("PlanReview")]
        write_state(tmp_state_file, make_state("review", agents=agents, plan_review_iteration=2))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("PlanReview", "Confidence: 50, Quality: 45"), store)
        state = store.load()
        assert state["phase"] == "failed"
        assert state["plan_review_status"] == "max_iterations_reached"

    def test_plan_review_scores_stored(self, tmp_state_file):
        agents = [running_agent("PlanReview")]
        write_state(tmp_state_file, make_state("review", agents=agents))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("PlanReview", "Confidence score: 90, Quality score: 85"), store)
        state = store.load()
        assert state["plan_review_scores"]["confidence"] == 90
        assert state["plan_review_scores"]["quality"] == 85


# ---------------------------------------------------------------------------
# TaskManager: advance to write-tests or write-code
# ---------------------------------------------------------------------------

class TestTaskManagerCompletion:
    def test_task_manager_tdd_advances_to_write_tests(self, tmp_state_file):
        agents = [running_agent("TaskManager")]
        write_state(tmp_state_file, make_state("task-create", agents=agents, tdd=True))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("TaskManager", "Tasks created."), store)
        state = store.load()
        assert state["phase"] == "write-tests"

    def test_task_manager_no_tdd_advances_to_write_code(self, tmp_state_file):
        agents = [running_agent("TaskManager")]
        write_state(tmp_state_file, make_state("task-create", agents=agents, tdd=False))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("TaskManager", "Tasks created."), store)
        state = store.load()
        assert state["phase"] == "write-code"


# ---------------------------------------------------------------------------
# TestReviewer: Pass/Fail verdict
# ---------------------------------------------------------------------------

class TestTestReviewerCompletion:
    def test_test_reviewer_pass_advances_to_write_code(self, tmp_state_file):
        agents = [running_agent("TestReviewer")]
        write_state(tmp_state_file, make_state("write-tests", agents=agents))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("TestReviewer", "Pass"), store)
        state = store.load()
        assert state["phase"] == "write-code"
        assert state["test_review_result"] == "Pass"

    def test_test_reviewer_fail_stays_in_write_tests(self, tmp_state_file):
        agents = [running_agent("TestReviewer")]
        write_state(tmp_state_file, make_state("write-tests", agents=agents))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("TestReviewer", "Fail"), store)
        state = store.load()
        assert state["phase"] == "write-tests"
        assert state["test_review_result"] == "Fail"


# ---------------------------------------------------------------------------
# Validator: Pass/Fail verdict
# ---------------------------------------------------------------------------

class TestValidatorCompletion:
    def test_validator_pass_advances_to_pr_create(self, tmp_state_file):
        agents = [running_agent("Validator")]
        write_state(tmp_state_file, make_state("validate", agents=agents))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("Validator", "Pass"), store)
        state = store.load()
        assert state["phase"] == "pr-create"
        assert state["validation_result"] == "Pass"

    def test_validator_fail_returns_to_write_code(self, tmp_state_file):
        agents = [running_agent("Validator")]
        write_state(tmp_state_file, make_state("validate", agents=agents))
        store = StateStore(tmp_state_file)
        review_guard.handle(stop_hook("Validator", "Fail"), store)
        state = store.load()
        assert state["phase"] == "write-code"
        assert state["validation_result"] == "Fail"

    def test_subagent_stop_always_returns_allow(self, tmp_state_file):
        write_state(tmp_state_file, make_state("validate"))
        store = StateStore(tmp_state_file)
        decision, _ = review_guard.handle(stop_hook("Validator", "Pass"), store)
        assert decision == "allow"
