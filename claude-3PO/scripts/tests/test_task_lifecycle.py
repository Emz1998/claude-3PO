"""Tests for the full task lifecycle in implement workflow.

PreToolUse → TaskCreate guard (validates parent metadata)
TaskCreated → records child under parent
TaskCompleted → marks child done, auto-completes parent when all children done
"""

import json
import pytest
from pathlib import Path
from lib.state_store import StateStore
from helpers import make_hook_input


# ═══════════════════════════════════════════════════════════════════
# State — subtask structure (dict, not string)
# ═══════════════════════════════════════════════════════════════════


class TestSubtaskDictStructure:
    def test_add_subtask_as_dict(self, state):
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": []},
        ])
        state.implement.add_subtask("T-001", {"task_id": "ct-1", "subject": "Write form", "status": "in_progress"})
        subs = state.implement.project_tasks[0]["subtasks"]
        assert len(subs) == 1
        assert subs[0]["task_id"] == "ct-1"
        assert subs[0]["status"] == "in_progress"

    def test_set_subtask_completed(self, state):
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": [
                {"task_id": "ct-1", "subject": "Write form", "status": "in_progress"},
            ]},
        ])
        state.implement.set_subtask_completed("T-001", "ct-1")
        subs = state.implement.project_tasks[0]["subtasks"]
        assert subs[0]["status"] == "completed"

    @staticmethod
    def _is_parent_complete(state, parent_id: str) -> bool:
        parent = next((pt for pt in state.implement.project_tasks if pt.get("id") == parent_id), None)
        subs = parent.get("subtasks", []) if parent else []
        return bool(subs) and all(
            (s.get("status") == "completed" if isinstance(s, dict) else False) for s in subs
        )

    def test_is_parent_complete(self, state):
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": [
                {"task_id": "ct-1", "subject": "Write form", "status": "completed"},
                {"task_id": "ct-2", "subject": "Add validation", "status": "completed"},
            ]},
        ])
        assert self._is_parent_complete(state, "T-001") is True

    def test_is_parent_not_complete(self, state):
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": [
                {"task_id": "ct-1", "subject": "Write form", "status": "completed"},
                {"task_id": "ct-2", "subject": "Add validation", "status": "in_progress"},
            ]},
        ])
        assert self._is_parent_complete(state, "T-001") is False

    def test_is_parent_no_subtasks_not_complete(self, state):
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": []},
        ])
        assert self._is_parent_complete(state, "T-001") is False

    def test_set_project_task_completed(self, state):
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": []},
        ])
        state.implement.set_project_task_completed("T-001")
        assert state.implement.project_tasks[0]["status"] == "completed"

    def test_get_parent_for_subtask(self, state):
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": [
                {"task_id": "ct-1", "subject": "Write form", "status": "in_progress"},
            ]},
            {"id": "T-002", "title": "Schema", "status": "in_progress", "subtasks": [
                {"task_id": "ct-2", "subject": "Create tables", "status": "in_progress"},
            ]},
        ])
        assert state.implement.get_parent_for_subtask("ct-1") == "T-001"
        assert state.implement.get_parent_for_subtask("ct-2") == "T-002"
        assert state.implement.get_parent_for_subtask("ct-999") is None

    def test_add_subtask_dedup_by_task_id(self, state):
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": []},
        ])
        state.implement.add_subtask("T-001", {"task_id": "ct-1", "subject": "Write form", "status": "in_progress"})
        state.implement.add_subtask("T-001", {"task_id": "ct-1", "subject": "Write form", "status": "in_progress"})
        assert len(state.implement.project_tasks[0]["subtasks"]) == 1


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — TaskCreate guard (implement workflow)
# ═══════════════════════════════════════════════════════════════════


class TestTaskCreateGuard:
    def test_blocks_missing_parent_task_id(self, config, state):
        from handlers.guardrails import TOOL_GUARDS
        state.set("workflow_type", "implement")
        state.add_phase("create-tasks")
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": []},
        ])
        hook = make_hook_input("TaskCreate", {
            "subject": "Write form",
            "description": "Implement login form",
            "metadata": {},  # missing parent_task_id
        })
        guard = TOOL_GUARDS.get("TaskCreate")
        assert guard is not None
        decision, msg = guard(hook, config, state)
        assert decision == "block"
        assert "parent_task_id" in msg

    def test_blocks_invalid_parent_task_id(self, config, state):
        from handlers.guardrails import TOOL_GUARDS
        state.set("workflow_type", "implement")
        state.add_phase("create-tasks")
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": []},
        ])
        hook = make_hook_input("TaskCreate", {
            "subject": "Write form",
            "description": "Implement login form",
            "metadata": {"parent_task_id": "T-999", "parent_task_title": "Ghost"},
        })
        guard = TOOL_GUARDS["TaskCreate"]
        decision, msg = guard(hook, config, state)
        assert decision == "block"
        assert "T-999" in msg

    def test_blocks_missing_parent_task_title(self, config, state):
        from handlers.guardrails import TOOL_GUARDS
        state.set("workflow_type", "implement")
        state.add_phase("create-tasks")
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": []},
        ])
        hook = make_hook_input("TaskCreate", {
            "subject": "Write form",
            "description": "Implement login form",
            "metadata": {"parent_task_id": "T-001"},  # missing title
        })
        guard = TOOL_GUARDS["TaskCreate"]
        decision, msg = guard(hook, config, state)
        assert decision == "block"
        assert "parent_task_title" in msg

    def test_allows_valid_metadata(self, config, state):
        from handlers.guardrails import TOOL_GUARDS
        state.set("workflow_type", "implement")
        state.add_phase("create-tasks")
        state.implement.set_project_tasks([
            {"id": "T-001", "title": "Build login", "status": "in_progress", "subtasks": []},
        ])
        hook = make_hook_input("TaskCreate", {
            "subject": "Write form",
            "description": "Implement login form",
            "metadata": {"parent_task_id": "T-001", "parent_task_title": "Build login"},
        })
        guard = TOOL_GUARDS["TaskCreate"]
        decision, msg = guard(hook, config, state)
        assert decision == "allow"

    def test_build_workflow_skips_metadata_check(self, config, state):
        from handlers.guardrails import TOOL_GUARDS
        state.set("workflow_type", "build")
        state.add_phase("write-tests")
        state.set_tasks(["Build login"])
        hook = make_hook_input("TaskCreate", {
            "subject": "Build login",
            "description": "Do it",
        })
        guard = TOOL_GUARDS["TaskCreate"]
        decision, _ = guard(hook, config, state)
        assert decision == "allow"
