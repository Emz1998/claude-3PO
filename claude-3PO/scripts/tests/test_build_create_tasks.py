"""Tests for create-tasks auto-phase in build workflow.

Build: tasks come from plan ## Tasks bullets (state.tasks).
Phase completes when all planned tasks have a matching entry in state.build.created_tasks.
"""

import pytest
from lib.state_store import StateStore
from utils.resolver import Resolver, resolve


class TestBuildCreatedTasks:
    """State tracking for build create-tasks."""

    def test_add_created_task(self, state):
        state.set("workflow_type", "build")
        state.set_tasks(["Build login", "Create schema"])
        state.build.add_created_task("Build login")
        assert "Build login" in state.build.created_tasks

    def test_add_created_task_dedup(self, state):
        state.set("workflow_type", "build")
        state.build.add_created_task("Build login")
        state.build.add_created_task("Build login")
        assert state.build.created_tasks.count("Build login") == 1

    def test_task_tracking_lists(self, state):
        state.set("workflow_type", "build")
        state.set_tasks(["Build login", "Create schema"])
        state.build.add_created_task("Build login")
        assert set(state.build.created_tasks) == {"Build login"}
        state.build.add_created_task("Create schema")
        assert set(state.build.created_tasks) == {"Build login", "Create schema"}

    def test_no_tasks_default(self, state):
        state.set("workflow_type", "build")
        assert state.tasks == []
        assert state.build.created_tasks == []

    def test_default_empty(self, state):
        assert state.build.created_tasks == []


class TestResolveCreateTasksBuild:
    """create-tasks resolver for build workflow."""

    def test_completes_when_all_created(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("create-tasks")
        state.set_tasks(["Build login", "Create schema"])
        state.build.add_created_task("Build login")
        state.build.add_created_task("Create schema")
        Resolver(config, state)._resolve_create_tasks()
        assert state.is_phase_completed("create-tasks")

    def test_does_not_complete_when_missing(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("create-tasks")
        state.set_tasks(["Build login", "Create schema"])
        state.build.add_created_task("Build login")
        Resolver(config, state)._resolve_create_tasks()
        assert not state.is_phase_completed("create-tasks")

    def test_dispatches_via_resolve(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("create-tasks")
        state.set_tasks(["Build login"])
        state.build.add_created_task("Build login")
        resolve(config, state)
        assert state.is_phase_completed("create-tasks")


class TestAutoTransitionBuildCreateTasks:
    """create-tasks auto-starts after plan-review in build workflow."""

    def test_plan_review_pass_does_not_auto_start(self, config, state):
        """plan-review pass is a checkpoint — does not auto-start create-tasks."""
        state.set("workflow_type", "build")
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 95, "quality_score": 95})
        resolve(config, state)
        assert state.is_phase_completed("plan-review")
        assert state.current_phase == "plan-review"  # checkpoint pause
