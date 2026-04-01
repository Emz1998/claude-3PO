"""Tests for guards/agent_guard.py (new unified version)."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow.guards import agent_guard
from workflow.state_store import StateStore


PHASES = ["explore", "plan", "write-plan", "review", "approved", "task-create",
          "write-tests", "write-code", "validate", "pr-create", "ci-check", "report", "completed"]


def make_state(phase: str, agents=None, **kwargs) -> dict:
    return {
        "workflow_active": True,
        "workflow_type": "implement",
        "phase": phase,
        "tdd": True,
        "skip_explore": False,
        "skip_research": False,
        "agents": agents or [],
        "plan_written": kwargs.get("plan_written", False),
        "plan_file": kwargs.get("plan_file", None),
        "tasks_created": kwargs.get("tasks_created", 0),
        "test_files_created": kwargs.get("test_files_created", []),
    }


def agent_hook(subagent_type: str, tool_use_id: str = "t1", run_in_background: bool = False) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {
            "subagent_type": subagent_type,
            "description": "x",
            "prompt": "x",
            "run_in_background": run_in_background,
        },
        "tool_use_id": tool_use_id,
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def write_state(tmp_state_file, state: dict) -> None:
    tmp_state_file.write_text(json.dumps(state))


# ---------------------------------------------------------------------------
# Workflow inactive — pass through
# ---------------------------------------------------------------------------

class TestWorkflowInactive:
    def test_no_workflow_active(self, tmp_state_file):
        tmp_state_file.write_text("{}")
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Explore"), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# Explore phase
# ---------------------------------------------------------------------------

class TestExplorePhase:
    def test_explore_allowed_in_explore_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("explore"))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Explore", "t1"), store)
        assert decision == "allow"

    def test_research_allowed_in_explore_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("explore"))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Research", "t1"), store)
        assert decision == "allow"

    def test_explore_max_3(self, tmp_state_file):
        agents = [{"agent_type": "Explore", "status": "running"} for _ in range(3)]
        write_state(tmp_state_file, make_state("explore", agents=agents))
        store = StateStore(tmp_state_file)
        decision, reason = agent_guard.validate(agent_hook("Explore", "t4"), store)
        assert decision == "block"
        assert "3" in reason or "Max" in reason

    def test_research_max_2(self, tmp_state_file):
        agents = [{"agent_type": "Research", "status": "running"} for _ in range(2)]
        write_state(tmp_state_file, make_state("explore", agents=agents))
        store = StateStore(tmp_state_file)
        decision, reason = agent_guard.validate(agent_hook("Research", "t3"), store)
        assert decision == "block"

    def test_explore_blocked_when_skip_explore(self, tmp_state_file):
        state = make_state("explore")
        state["skip_explore"] = True
        write_state(tmp_state_file, state)
        store = StateStore(tmp_state_file)
        decision, reason = agent_guard.validate(agent_hook("Explore"), store)
        assert decision == "block"
        assert "skip" in reason.lower()

    def test_research_blocked_when_skip_research(self, tmp_state_file):
        state = make_state("explore")
        state["skip_research"] = True
        write_state(tmp_state_file, state)
        store = StateStore(tmp_state_file)
        decision, reason = agent_guard.validate(agent_hook("Research"), store)
        assert decision == "block"

    def test_background_explore_blocked(self, tmp_state_file):
        write_state(tmp_state_file, make_state("explore"))
        store = StateStore(tmp_state_file)
        decision, reason = agent_guard.validate(agent_hook("Explore", run_in_background=True), store)
        assert decision == "block"
        assert "background" in reason.lower()

    def test_background_research_blocked(self, tmp_state_file):
        write_state(tmp_state_file, make_state("explore"))
        store = StateStore(tmp_state_file)
        decision, reason = agent_guard.validate(agent_hook("Research", run_in_background=True), store)
        assert decision == "block"

    def test_plan_agent_blocked_in_explore_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("explore"))
        store = StateStore(tmp_state_file)
        decision, reason = agent_guard.validate(agent_hook("Plan"), store)
        assert decision == "block"
        assert "explore" in reason.lower() or "plan" in reason.lower()

    def test_agent_recorded_on_allow(self, tmp_state_file):
        write_state(tmp_state_file, make_state("explore"))
        store = StateStore(tmp_state_file)
        agent_guard.validate(agent_hook("Explore", "t1"), store)
        state = store.load()
        assert any(a["agent_type"] == "Explore" and a["tool_use_id"] == "t1"
                   for a in state["agents"])


# ---------------------------------------------------------------------------
# Plan phase
# ---------------------------------------------------------------------------

class TestPlanPhase:
    def test_plan_agent_allowed_in_plan_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("plan"))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Plan"), store)
        assert decision == "allow"

    def test_plan_agent_max_1(self, tmp_state_file):
        agents = [{"agent_type": "Plan", "status": "running"}]
        write_state(tmp_state_file, make_state("plan", agents=agents))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Plan", "t2"), store)
        assert decision == "block"

    def test_non_plan_agent_blocked_in_plan_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("plan"))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Explore"), store)
        assert decision == "block"


# ---------------------------------------------------------------------------
# Review phase
# ---------------------------------------------------------------------------

class TestReviewPhase:
    def test_plan_review_allowed_in_review_phase_with_plan(self, tmp_state_file):
        write_state(tmp_state_file, make_state("review", plan_written=True, plan_file=".claude/plans/p.md"))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("PlanReview"), store)
        assert decision == "allow"

    def test_plan_review_blocked_without_plan_written(self, tmp_state_file):
        write_state(tmp_state_file, make_state("review", plan_written=False))
        store = StateStore(tmp_state_file)
        decision, reason = agent_guard.validate(agent_hook("PlanReview"), store)
        assert decision == "block"
        assert "plan" in reason.lower()

    def test_plan_review_max_3(self, tmp_state_file):
        agents = [{"agent_type": "PlanReview", "status": "completed"} for _ in range(3)]
        write_state(tmp_state_file, make_state("review", agents=agents, plan_written=True, plan_file=".claude/plans/p.md"))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("PlanReview"), store)
        assert decision == "block"

    def test_non_review_agent_blocked_in_review_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("review", plan_written=True))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Explore"), store)
        assert decision == "block"


# ---------------------------------------------------------------------------
# Task-create phase
# ---------------------------------------------------------------------------

class TestTaskCreatePhase:
    def test_task_manager_allowed_in_task_create(self, tmp_state_file):
        write_state(tmp_state_file, make_state("task-create"))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("TaskManager"), store)
        assert decision == "allow"

    def test_task_manager_max_1(self, tmp_state_file):
        agents = [{"agent_type": "TaskManager", "status": "running"}]
        write_state(tmp_state_file, make_state("task-create", agents=agents))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("TaskManager"), store)
        assert decision == "block"


# ---------------------------------------------------------------------------
# Write-tests phase
# ---------------------------------------------------------------------------

class TestWriteTestsPhase:
    def test_test_reviewer_allowed_with_test_files(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests", test_files_created=["tests/test_foo.py"]))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("TestReviewer"), store)
        assert decision == "allow"

    def test_test_reviewer_blocked_without_test_files(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests", test_files_created=[]))
        store = StateStore(tmp_state_file)
        decision, reason = agent_guard.validate(agent_hook("TestReviewer"), store)
        assert decision == "block"
        assert "test" in reason.lower()

    def test_non_test_reviewer_blocked_in_write_tests(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Validator"), store)
        assert decision == "block"


# ---------------------------------------------------------------------------
# Write-code phase — Validator triggers validate phase
# ---------------------------------------------------------------------------

class TestWriteCodePhase:
    def test_validator_allowed_in_write_code(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Validator"), store)
        assert decision == "allow"

    def test_validator_advances_to_validate_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = StateStore(tmp_state_file)
        agent_guard.validate(agent_hook("Validator"), store)
        state = store.load()
        assert state["phase"] == "validate"

    def test_non_validator_blocked_in_write_code(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Explore"), store)
        assert decision == "block"


# ---------------------------------------------------------------------------
# Validate phase
# ---------------------------------------------------------------------------

class TestValidatePhase:
    def test_validator_allowed_in_validate(self, tmp_state_file):
        write_state(tmp_state_file, make_state("validate"))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Validator"), store)
        assert decision == "allow"

    def test_non_validator_blocked_in_validate(self, tmp_state_file):
        write_state(tmp_state_file, make_state("validate"))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Explore"), store)
        assert decision == "block"


# ---------------------------------------------------------------------------
# Blocked phases
# ---------------------------------------------------------------------------

class TestBlockedPhases:
    @pytest.mark.parametrize("phase", ["write-plan", "approved", "pr-create", "ci-check", "report", "completed"])
    def test_agents_blocked_in_non_agent_phases(self, phase, tmp_state_file):
        write_state(tmp_state_file, make_state(phase))
        store = StateStore(tmp_state_file)
        decision, _ = agent_guard.validate(agent_hook("Explore"), store)
        assert decision == "block"
