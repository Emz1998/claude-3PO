"""Tests for :class:`ImplementState` — implement-workflow slice of StateStore.

Exercises the nine implement-only accessors (project_tasks/set, add_subtask,
set_subtask_completed, set_project_task_completed, get_parent_for_subtask,
plan_files_to_modify/set, add_project_task) and confirms they delegate
through the shared :class:`BaseState`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.state_store import StateStore
from models.state import Task


@pytest.fixture
def store(tmp_path: Path) -> StateStore:
    # Fresh StateStore per test; no default state so we start empty.
    return StateStore(tmp_path / "state.json")


class TestImplementProjectTasks:
    """project_tasks / set_project_tasks round-trip through the shared base."""

    def test_default_empty(self, store: StateStore):
        assert store.implement.project_tasks == []

    def test_set_and_read(self, store: StateStore):
        store.implement.set_project_tasks([{"id": "T-1", "title": "x"}])
        # Slice reads flow back through the shared JSON document.
        assert store.implement.project_tasks[0]["id"] == "T-1"
        assert store.load()["project_tasks"][0]["id"] == "T-1"


class TestImplementSubtaskOps:
    """Subtask add / complete / parent-lookup operations."""

    def test_add_subtask_string(self, store: StateStore):
        store.implement.set_project_tasks([{"id": "T-1"}])
        store.implement.add_subtask("T-1", "child")
        assert store.implement.project_tasks[0]["subtasks"] == ["child"]

    def test_add_subtask_dict_dedup_by_task_id(self, store: StateStore):
        store.implement.set_project_tasks([{"id": "T-1"}])
        store.implement.add_subtask("T-1", {"task_id": "c1"})
        store.implement.add_subtask("T-1", {"task_id": "c1"})
        assert len(store.implement.project_tasks[0]["subtasks"]) == 1

    def test_set_subtask_completed(self, store: StateStore):
        store.implement.set_project_tasks([{"id": "T-1"}])
        store.implement.add_subtask("T-1", {"task_id": "c1"})
        store.implement.set_subtask_completed("T-1", "c1")
        sub = store.implement.project_tasks[0]["subtasks"][0]
        assert sub["status"] == "completed"

    def test_set_project_task_completed(self, store: StateStore):
        store.implement.set_project_tasks([{"id": "T-1"}])
        store.implement.set_project_task_completed("T-1")
        assert store.implement.project_tasks[0]["status"] == "completed"

    def test_get_parent_for_subtask(self, store: StateStore):
        store.implement.set_project_tasks([{"id": "T-1"}])
        store.implement.add_subtask("T-1", {"task_id": "c1"})
        assert store.implement.get_parent_for_subtask("c1") == "T-1"
        assert store.implement.get_parent_for_subtask("missing") is None


class TestImplementPlanFilesToModify:
    """plan_files_to_modify / setter round-trip."""

    def test_default_empty(self, store: StateStore):
        assert store.implement.plan_files_to_modify == []

    def test_set_and_read(self, store: StateStore):
        store.implement.set_plan_files_to_modify(["a.py", "b.py"])
        assert store.implement.plan_files_to_modify == ["a.py", "b.py"]


class TestImplementAddProjectTaskSink:
    """add_project_task — Recorder-facing dedup-by-task_id sink."""

    def test_appends_task(self, store: StateStore):
        store.implement.add_project_task(Task(task_id="T-1", subject="s", description="d"))
        assert store.implement.project_tasks[0]["task_id"] == "T-1"

    def test_dedup_by_task_id(self, store: StateStore):
        store.implement.add_project_task(Task(task_id="T-1", subject="a", description=""))
        store.implement.add_project_task(Task(task_id="T-1", subject="b", description=""))
        assert len(store.implement.project_tasks) == 1


class TestImplementSliceSharesBase:
    """Writes through the slice are visible via the facade and the base."""

    def test_slice_write_visible_through_facade(self, store: StateStore):
        store.implement.set_plan_files_to_modify(["x.py"])
        # Same JSON document — facade sees what the slice wrote.
        assert store.load()["plan_files_to_modify"] == ["x.py"]
