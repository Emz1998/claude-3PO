"""Tests for create-tasks phase — implement workflow.

Validates TaskCreate with parent_task_id/title matching project tasks,
subtask recording, and auto-advance when all project tasks have subtasks.
"""

import pytest
from utils.resolver import resolve_create_tasks, resolve
from lib.state_store import StateStore


class TestResolveCreateTasks:
    def test_completes_when_all_tasks_have_subtasks(self, state):
        state.add_phase("create-tasks")
        state.set_project_tasks([
            {"id": "T-001", "title": "Build login", "subtasks": ["Sub 1"]},
            {"id": "T-002", "title": "Create schema", "subtasks": ["Sub 2"]},
        ])
        resolve_create_tasks(state)
        assert state.is_phase_completed("create-tasks")

    def test_does_not_complete_when_missing_subtasks(self, state):
        state.add_phase("create-tasks")
        state.set_project_tasks([
            {"id": "T-001", "title": "Build login", "subtasks": ["Sub 1"]},
            {"id": "T-002", "title": "Create schema", "subtasks": []},
        ])
        resolve_create_tasks(state)
        assert not state.is_phase_completed("create-tasks")

    def test_does_not_complete_when_no_project_tasks(self, state):
        state.add_phase("create-tasks")
        resolve_create_tasks(state)
        assert not state.is_phase_completed("create-tasks")

    def test_dispatches_via_resolve(self, config, state):
        state.set("workflow_type", "implement")
        state.add_phase("create-tasks")
        state.set_project_tasks([
            {"id": "T-001", "title": "Build login", "subtasks": ["Sub 1"]},
        ])
        resolve(config, state)
        assert state.is_phase_completed("create-tasks")


class TestImplementTaskCreatedValidation:
    """TaskCreated in implement workflow validates parent_task_id matching project tasks."""

    def test_subtask_recorded(self, state):
        state.set_project_tasks([
            {"id": "T-001", "title": "Build login", "subtasks": []},
        ])
        state.add_subtask("T-001", "Implement login form")
        ptasks = state.project_tasks
        assert "Implement login form" in ptasks[0]["subtasks"]

    def test_mismatched_parent_not_recorded(self, state):
        state.set_project_tasks([
            {"id": "T-001", "title": "Build login", "subtasks": []},
        ])
        # Try to add subtask to non-existent parent
        state.add_subtask("T-999", "Ghost subtask")
        ptasks = state.project_tasks
        assert ptasks[0]["subtasks"] == []
