"""Tests for recorder.py — SubagentStop recording logic."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow import recorder
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
        recorder.record_subagent_stop(stop_hook("Explore"), store)
        state = store.load()
        completed = [a for a in state["agents"] if a["agent_type"] == "Explore" and a["status"] == "completed"]
        assert len(completed) == 1

    def test_all_explore_done_advances_to_write_codebase(self, tmp_state_file):
        agents = (
            [{"agent_type": "Explore", "status": "completed"}] * 2 +
            [running_agent("Explore")] +
            [{"agent_type": "Research", "status": "completed"}] * 2
        )
        write_state(tmp_state_file, make_state("explore", agents=agents))
        store = StateStore(tmp_state_file)
        recorder.record_subagent_stop(stop_hook("Explore"), store)
        state = store.load()
        assert state["phase"] == "write-codebase"

    def test_partial_explore_does_not_advance(self, tmp_state_file):
        agents = [running_agent("Explore")]  # only 1 of 3
        write_state(tmp_state_file, make_state("explore", agents=agents))
        store = StateStore(tmp_state_file)
        recorder.record_subagent_stop(stop_hook("Explore"), store)
        state = store.load()
        assert state["phase"] == "explore"

    def test_skip_explore_only_needs_research(self, tmp_state_file):
        agents = [running_agent("Research"), {"agent_type": "Research", "status": "completed"}]
        state = make_state("explore", agents=agents, skip_explore=True)
        write_state(tmp_state_file, state)
        store = StateStore(tmp_state_file)
        recorder.record_subagent_stop(stop_hook("Research"), store)
        state = store.load()
        assert state["phase"] == "write-codebase"

    def test_skip_research_only_needs_explore(self, tmp_state_file):
        agents = (
            [{"agent_type": "Explore", "status": "completed"}] * 2 +
            [running_agent("Explore")]
        )
        state = make_state("explore", agents=agents, skip_research=True)
        write_state(tmp_state_file, state)
        store = StateStore(tmp_state_file)
        recorder.record_subagent_stop(stop_hook("Explore"), store)
        state = store.load()
        assert state["phase"] == "write-codebase"


# ---------------------------------------------------------------------------
# Write-codebase: advance to plan on CODEBASE.md write
# ---------------------------------------------------------------------------

class TestWriteCodebasePhase:
    def _write_hook(self, file_path: str) -> dict:
        return {
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": file_path, "content": "# Codebase"},
            "tool_response": {"type": "update", "filePath": file_path},
            "tool_use_id": "t1",
            "session_id": "s",
            "transcript_path": "t",
            "cwd": ".",
            "permission_mode": "default",
        }

    def test_codebase_md_write_advances_to_plan(self, tmp_state_file):
        state = make_state("write-codebase")
        write_state(tmp_state_file, state)
        store = StateStore(tmp_state_file)
        decision, _ = recorder.record_write(self._write_hook("CODEBASE.md"), store)
        assert decision == "allow"
        state = store.load()
        assert state["phase"] == "plan"
        assert state["codebase_written"] is True

    def test_non_codebase_write_does_not_advance(self, tmp_state_file):
        state = make_state("write-codebase")
        write_state(tmp_state_file, state)
        store = StateStore(tmp_state_file)
        recorder.record_write(self._write_hook("README.md"), store)
        state = store.load()
        assert state["phase"] == "write-codebase"


# ---------------------------------------------------------------------------
# Plan: advance to write-plan
# ---------------------------------------------------------------------------

class TestPlanCompletion:
    def test_plan_stop_advances_to_write_plan(self, tmp_state_file):
        agents = [running_agent("Plan")]
        write_state(tmp_state_file, make_state("plan", agents=agents))
        store = StateStore(tmp_state_file)
        recorder.record_subagent_stop(stop_hook("Plan", "I have created the plan."), store)
        state = store.load()
        assert state["phase"] == "write-plan"


# ---------------------------------------------------------------------------
# PlanReview: parse scores, advance or iterate
# ---------------------------------------------------------------------------

class TestPlanReviewCompletion:
    def test_plan_review_approved_advances_to_present_plan(self, tmp_state_file):
        agents = [running_agent("PlanReview")]
        write_state(tmp_state_file, make_state("review", agents=agents))
        store = StateStore(tmp_state_file)
        recorder.record_subagent_stop(stop_hook("PlanReview", "Confidence score: 90, Quality score: 85"), store)
        state = store.load()
        assert state["phase"] == "present-plan"
        assert state["plan_review_status"] == "approved"

    def test_plan_review_failing_increments_iteration(self, tmp_state_file):
        agents = [running_agent("PlanReview")]
        write_state(tmp_state_file, make_state("review", agents=agents))
        store = StateStore(tmp_state_file)
        recorder.record_subagent_stop(stop_hook("PlanReview", "Confidence: 50, Quality: 45"), store)
        state = store.load()
        assert state["phase"] == "review"
        assert state["plan_review_iteration"] == 1
        assert state["plan_review_status"] == "revision_needed"

    def test_plan_review_max_iterations_sets_failed(self, tmp_state_file):
        agents = [running_agent("PlanReview")]
        write_state(tmp_state_file, make_state("review", agents=agents, plan_review_iteration=2))
        store = StateStore(tmp_state_file)
        recorder.record_subagent_stop(stop_hook("PlanReview", "Confidence: 50, Quality: 45"), store)
        state = store.load()
        assert state["phase"] == "failed"
        assert state["plan_review_status"] == "max_iterations_reached"

    def test_plan_review_scores_stored(self, tmp_state_file):
        agents = [running_agent("PlanReview")]
        write_state(tmp_state_file, make_state("review", agents=agents))
        store = StateStore(tmp_state_file)
        recorder.record_subagent_stop(stop_hook("PlanReview", "Confidence score: 90, Quality score: 85"), store)
        state = store.load()
        assert state["plan_review_scores"]["confidence"] == 90
        assert state["plan_review_scores"]["quality"] == 85


# ---------------------------------------------------------------------------
# TestReviewer: Pass/Fail verdict
# ---------------------------------------------------------------------------

class TestTestReviewerCompletion:
    def test_test_reviewer_pass_advances_to_write_code(self, tmp_state_file):
        agents = [running_agent("TestReviewer")]
        write_state(tmp_state_file, make_state("write-tests", agents=agents))
        store = StateStore(tmp_state_file)
        recorder.record_subagent_stop(stop_hook("TestReviewer", "Pass"), store)
        state = store.load()
        assert state["phase"] == "write-code"
        assert state["test_review_result"] == "Pass"

    def test_test_reviewer_fail_stays_in_write_tests(self, tmp_state_file):
        agents = [running_agent("TestReviewer")]
        write_state(tmp_state_file, make_state("write-tests", agents=agents))
        store = StateStore(tmp_state_file)
        recorder.record_subagent_stop(stop_hook("TestReviewer", "Fail"), store)
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
        recorder.record_subagent_stop(stop_hook("Validator", "Pass"), store)
        state = store.load()
        assert state["phase"] == "pr-create"
        assert state["validation_result"] == "Pass"

    def test_validator_fail_returns_to_write_code(self, tmp_state_file):
        agents = [running_agent("Validator")]
        write_state(tmp_state_file, make_state("validate", agents=agents))
        store = StateStore(tmp_state_file)
        recorder.record_subagent_stop(stop_hook("Validator", "Fail"), store)
        state = store.load()
        assert state["phase"] == "write-code"
        assert state["validation_result"] == "Fail"

    def test_subagent_stop_always_returns_allow(self, tmp_state_file):
        write_state(tmp_state_file, make_state("validate"))
        store = StateStore(tmp_state_file)
        decision, _ = recorder.record_subagent_stop(stop_hook("Validator", "Pass"), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# record_agent_from_hook: agent recording from raw hook_input
# ---------------------------------------------------------------------------

def agent_hook(agent_type: str, tool_use_id: str = "tu1") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_use_id": tool_use_id,
        "tool_input": {"subagent_type": agent_type},
    }


class TestRecordAgentFromHook:
    def test_records_agent_entry(self, tmp_state_file):
        write_state(tmp_state_file, make_state("explore"))
        store = StateStore(tmp_state_file)
        decision, _ = recorder.record_agent_from_hook(agent_hook("Explore", "tu1"), store)
        assert decision == "allow"
        state = store.load()
        assert len(state["agents"]) == 1
        assert state["agents"][0]["agent_type"] == "Explore"
        assert state["agents"][0]["status"] == "running"
        assert state["agents"][0]["tool_use_id"] == "tu1"

    def test_validator_advances_phase_from_write_code(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = StateStore(tmp_state_file)
        decision, _ = recorder.record_agent_from_hook(agent_hook("Validator"), store)
        assert decision == "allow"
        state = store.load()
        assert state["phase"] == "validate"
        assert len(state["agents"]) == 1
        assert state["agents"][0]["agent_type"] == "Validator"

    def test_validator_in_validate_phase_does_not_advance(self, tmp_state_file):
        write_state(tmp_state_file, make_state("validate"))
        store = StateStore(tmp_state_file)
        recorder.record_agent_from_hook(agent_hook("Validator"), store)
        state = store.load()
        assert state["phase"] == "validate"

    def test_inactive_workflow_skips_recording(self, tmp_state_file):
        write_state(tmp_state_file, {"workflow_active": False})
        store = StateStore(tmp_state_file)
        decision, _ = recorder.record_agent_from_hook(agent_hook("Explore"), store)
        assert decision == "allow"
        state = store.load()
        assert "agents" not in state

    def test_always_returns_allow(self, tmp_state_file):
        write_state(tmp_state_file, make_state("explore"))
        store = StateStore(tmp_state_file)
        decision, reason = recorder.record_agent_from_hook(agent_hook("Explore"), store)
        assert decision == "allow"
        assert reason == ""


# ---------------------------------------------------------------------------
# advance_after_plan_approval
# ---------------------------------------------------------------------------

class TestAdvanceAfterPlanApproval:
    def test_advance_to_task_create_with_story_id(self, tmp_state_file):
        write_state(tmp_state_file, make_state("present-plan", story_id="SK-001"))
        store = StateStore(tmp_state_file)
        result = recorder.advance_after_plan_approval(store)
        assert result == "task-create"
        assert store.load()["phase"] == "task-create"

    def test_advance_to_write_tests_with_tdd(self, tmp_state_file):
        write_state(tmp_state_file, make_state("present-plan", tdd=True))
        store = StateStore(tmp_state_file)
        result = recorder.advance_after_plan_approval(store)
        assert result == "write-tests"
        assert store.load()["phase"] == "write-tests"

    def test_advance_to_write_code_default(self, tmp_state_file):
        write_state(tmp_state_file, make_state("present-plan", tdd=False))
        store = StateStore(tmp_state_file)
        result = recorder.advance_after_plan_approval(store)
        assert result == "write-code"
        assert store.load()["phase"] == "write-code"

    def test_no_advance_for_plan_workflow(self, tmp_state_file):
        write_state(tmp_state_file, make_state("present-plan", workflow_type="plan"))
        store = StateStore(tmp_state_file)
        result = recorder.advance_after_plan_approval(store)
        assert result is None
        assert store.load()["phase"] == "present-plan"

    def test_no_advance_when_inactive(self, tmp_state_file):
        write_state(tmp_state_file, {"workflow_active": False, "phase": "present-plan"})
        store = StateStore(tmp_state_file)
        result = recorder.advance_after_plan_approval(store)
        assert result is None
