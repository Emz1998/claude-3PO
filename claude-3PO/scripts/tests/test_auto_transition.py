"""Tests for auto-transition phases.

Auto phases (clarify, create-tasks, write-tests, write-code) are started
automatically by the resolver / initializer after the previous phase completes.

The build phase order is:
    clarify (auto) → explore → research → decision → plan → plan-review →
    create-tasks (auto) → write-tests (auto, TDD) → test-review (TDD) →
    write-code (auto) → quality-check → code-review → pr-create → ci-check →
    write-report
"""

import pytest
from models.state import Agent
from guardrails import phase_guard
from utils.resolver import resolve
from lib.state_store import StateStore


class TestAutoTransitionBuild:
    """Build workflow auto-transitions after clarify removal."""

    def test_write_tests_auto_starts_after_create_tasks_tdd(self, config, state):
        state.set("workflow_type", "build")
        state.set("tdd", True)
        state.add_phase("create-tasks")
        state.set_tasks(["Build login"])
        state.add_created_task("Build login")
        resolve(config, state)
        assert state.is_phase_completed("create-tasks")
        assert state.current_phase == "write-tests"

    def test_write_code_auto_starts_after_test_review_pass(self, config, state):
        state.set("workflow_type", "build")
        state.set("tdd", True)
        state.add_phase("test-review")
        state.add_test_review("Pass")
        resolve(config, state)
        assert state.is_phase_completed("test-review")
        assert state.current_phase == "write-code"

    def test_write_code_auto_starts_after_create_tasks_non_tdd(self, config, state):
        state.set("workflow_type", "build")
        state.set("tdd", False)
        state.add_phase("create-tasks")
        state.set_tasks(["Build login"])
        state.add_created_task("Build login")
        resolve(config, state)
        assert state.is_phase_completed("create-tasks")
        assert state.current_phase == "write-code"


class TestAutoTransitionImplement:
    """Implement workflow: create-tasks auto-starts after plan-review pass."""

    def test_plan_review_pass_does_not_auto_start_create_tasks(self, config, state):
        """plan-review pass is a checkpoint — does not auto-start next phase."""
        state.set("workflow_type", "implement")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 95, "quality_score": 95})
        resolve(config, state)
        assert state.is_phase_completed("plan-review")
        assert state.current_phase == "plan-review"  # checkpoint pause

    def test_write_tests_auto_starts_after_create_tasks(self, config, state):
        state.set("workflow_type", "implement")
        state.set("tdd", True)
        state.add_phase("create-tasks")
        state.set_project_tasks([
            {"id": "T-001", "title": "Task", "subtasks": ["Sub"]},
        ])
        resolve(config, state)
        assert state.is_phase_completed("create-tasks")
        assert state.current_phase == "write-tests"

    def test_write_code_auto_starts_after_tests_review(self, config, state):
        state.set("workflow_type", "implement")
        state.set("tdd", True)
        state.add_phase("tests-review")
        state.add_test_review("Pass")
        resolve(config, state)
        assert state.is_phase_completed("tests-review")
        assert state.current_phase == "write-code"

    def test_write_code_auto_starts_after_create_tasks_non_tdd(self, config, state):
        state.set("workflow_type", "implement")
        state.set("tdd", False)
        state.add_phase("create-tasks")
        state.set_project_tasks([
            {"id": "T-001", "title": "Task", "subtasks": ["Sub"]},
        ])
        resolve(config, state)
        assert state.is_phase_completed("create-tasks")
        assert state.current_phase == "write-code"


class TestAutoPhaseNotSkillInvoked:
    """Auto phases must not be invokable via skill command."""

    def test_create_tasks_blocks_as_skill(self, config, state):
        from helpers import make_hook_input

        state.set("workflow_type", "implement")
        state.add_phase("plan-review")
        state.set_phase_completed("plan-review")
        hook = make_hook_input("Skill", {"skill": "create-tasks"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "block"

    def test_write_tests_blocks_as_skill(self, config, state):
        from helpers import make_hook_input

        state.set("workflow_type", "build")
        state.add_phase("test-review")
        state.set_phase_completed("test-review")
        hook = make_hook_input("Skill", {"skill": "write-tests"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "block"

    def test_write_code_blocks_as_skill(self, config, state):
        from helpers import make_hook_input

        state.set("workflow_type", "build")
        state.add_phase("test-review")
        state.set_phase_completed("test-review")
        hook = make_hook_input("Skill", {"skill": "write-code"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "block"

    def test_clarify_blocks_as_skill(self, config, state):
        from helpers import make_hook_input

        state.set("workflow_type", "build")
        # clarify is the first phase; even with no phases active, invoking it
        # as a skill should block since it's an auto-phase.
        hook = make_hook_input("Skill", {"skill": "clarify"})
        decision, msg = phase_guard(hook, config, state)
        assert decision == "block"
        assert "auto-phase" in msg.lower()
