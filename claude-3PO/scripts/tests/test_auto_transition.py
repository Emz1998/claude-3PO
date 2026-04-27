"""Tests for auto-transition phases.

Auto phases (create-tasks, write-tests, write-code) are started
automatically by the resolver / initializer after the previous phase completes.

The trimmed 7-phase implement order is:
    explore → research → plan (checkpoint) → create-tasks (auto) →
    write-tests (auto, TDD) → write-code (auto) → write-report
"""

import pytest
from models.state import Agent
from handlers.guardrails import phase_guard
from utils.resolver import resolve
from lib.state_store import StateStore


class TestAutoTransitionImplement:
    """Implement workflow: plan completion is a checkpoint, write-tests auto-starts."""

    def test_plan_completion_does_not_auto_start_create_tasks(self, config, state):
        """plan completion is a checkpoint — does not auto-start next phase."""
        state.set("workflow_type", "implement")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        state.set_plan_file_path(".claude/plans/latest-plan.md")
        state.set_plan_written(True)
        resolve(config, state)
        assert state.is_phase_completed("plan")
        assert state.current_phase == "plan"  # checkpoint pause

    def test_write_tests_auto_starts_after_create_tasks(self, config, state):
        state.set("workflow_type", "implement")
        state.set("tdd", True)
        state.add_phase("create-tasks")
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Task", "subtasks": ["Sub"]},
        ])
        resolve(config, state)
        assert state.is_phase_completed("create-tasks")
        assert state.current_phase == "write-tests"

    def test_write_code_auto_starts_after_create_tasks_non_tdd(self, config, state):
        state.set("workflow_type", "implement")
        state.set("tdd", False)
        state.add_phase("create-tasks")
        state.implement.set_project_tasks([
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
        state.add_phase("plan")
        state.set_phase_completed("plan")
        hook = make_hook_input("Skill", {"skill": "create-tasks"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "block"

    def test_write_tests_blocks_as_skill(self, config, state):
        from helpers import make_hook_input

        state.set("workflow_type", "implement")
        state.add_phase("create-tasks")
        state.set_phase_completed("create-tasks")
        hook = make_hook_input("Skill", {"skill": "write-tests"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "block"

    def test_write_code_blocks_as_skill(self, config, state):
        from helpers import make_hook_input

        state.set("workflow_type", "implement")
        state.add_phase("write-tests")
        state.set_phase_completed("write-tests")
        hook = make_hook_input("Skill", {"skill": "write-code"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "block"
