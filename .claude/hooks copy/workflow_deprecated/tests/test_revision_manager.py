#!/usr/bin/env python3
"""Pytest tests for the revision_manager module."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from validators.revision_manager import (  # type: ignore
    create_revision_tasks,
    save_revision_tasks,
    load_revision_tasks,
    inject_revision_tasks_into_state,
    get_next_revision_round,
    _get_revisions_path,
)

REVISIONS_DIR = Path("/tmp/claude/test_revisions")


@pytest.fixture(autouse=True)
def cleanup_revisions():
    """Clean up test revision files before and after each test."""
    if REVISIONS_DIR.exists():
        import shutil

        shutil.rmtree(REVISIONS_DIR)
    yield
    if REVISIONS_DIR.exists():
        import shutil

        shutil.rmtree(REVISIONS_DIR)


class TestCreateRevisionTasks:
    """Tests for create_revision_tasks function."""

    def test_creates_tasks_from_failed_criteria(self):
        """Creates revision tasks from failed criteria list."""
        failed = [
            {"id": "AC-010", "description": "User can log in"},
            {"id": "AC-011", "description": "Error messages display"},
        ]
        tasks = create_revision_tasks(failed, "ac_validation", 1)

        assert len(tasks) == 2
        assert tasks[0]["id"] == "RT-1-001"
        assert tasks[1]["id"] == "RT-1-002"

    def test_task_has_required_fields(self):
        """Each revision task has all required fields."""
        failed = [{"id": "AC-010", "description": "User can log in"}]
        tasks = create_revision_tasks(failed, "ac_validation", 1)

        task = tasks[0]
        assert "id" in task
        assert "description" in task
        assert "source_criteria" in task
        assert "status" in task
        assert "created" in task

    def test_task_id_format_matches_round(self):
        """Task IDs use correct round number."""
        failed = [{"id": "SC-001", "description": "Feature works"}]
        tasks = create_revision_tasks(failed, "sc_validation", 3)

        assert tasks[0]["id"] == "RT-3-001"

    def test_task_status_is_not_started(self):
        """New revision tasks have not_started status."""
        failed = [{"id": "AC-001", "description": "Test"}]
        tasks = create_revision_tasks(failed, "ac_validation", 1)

        assert tasks[0]["status"] == "not_started"

    def test_task_description_includes_criteria(self):
        """Task description references the failed criteria."""
        failed = [{"id": "AC-010", "description": "User can log in"}]
        tasks = create_revision_tasks(failed, "ac_validation", 1)

        assert "User can log in" in tasks[0]["description"]

    def test_source_criteria_set(self):
        """Source criteria links back to the failed criterion."""
        failed = [{"id": "AC-010", "description": "Test"}]
        tasks = create_revision_tasks(failed, "ac_validation", 1)

        assert tasks[0]["source_criteria"] == "AC-010"

    def test_empty_criteria_returns_empty(self):
        """Empty failed criteria list returns empty tasks."""
        tasks = create_revision_tasks([], "ac_validation", 1)
        assert tasks == []

    def test_sequential_numbering(self):
        """Tasks are numbered sequentially with zero-padding."""
        failed = [
            {"id": f"AC-{i:03d}", "description": f"Criteria {i}"} for i in range(1, 4)
        ]
        tasks = create_revision_tasks(failed, "ac_validation", 2)

        assert tasks[0]["id"] == "RT-2-001"
        assert tasks[1]["id"] == "RT-2-002"
        assert tasks[2]["id"] == "RT-2-003"


class TestSaveAndLoadRevisionTasks:
    """Tests for save_revision_tasks and load_revision_tasks."""

    @patch("validators.revision_manager.PROJECT_ROOT", REVISIONS_DIR)
    def test_save_creates_file(self):
        """save_revision_tasks creates the JSON file."""
        tasks = [{"id": "RT-1-001", "description": "Fix", "status": "not_started"}]
        save_revision_tasks(tasks, "v0.1.0", "EPIC-001", "FEAT-001")

        path = (
            REVISIONS_DIR
            / "project"
            / "v0.1.0"
            / "EPIC-001"
            / "FEAT-001"
            / "revisions"
            / "revision_tasks.json"
        )
        assert path.exists()

    @patch("validators.revision_manager.PROJECT_ROOT", REVISIONS_DIR)
    def test_save_creates_directories(self):
        """save_revision_tasks creates parent directories."""
        tasks = [{"id": "RT-1-001", "description": "Fix", "status": "not_started"}]
        save_revision_tasks(tasks, "v0.1.0", "EPIC-002", "FEAT-005")

        path = (
            REVISIONS_DIR / "project" / "v0.1.0" / "EPIC-002" / "FEAT-005" / "revisions"
        )
        assert path.is_dir()

    @patch("validators.revision_manager.PROJECT_ROOT", REVISIONS_DIR)
    def test_load_returns_saved_data(self):
        """load_revision_tasks returns previously saved data."""
        tasks = [{"id": "RT-1-001", "description": "Fix", "status": "not_started"}]
        save_revision_tasks(
            tasks,
            "v0.1.0",
            "EPIC-001",
            "FEAT-001",
            criteria_type="ac_validation",
            round_num=1,
            failed_criteria=[{"id": "AC-010", "status": "unmet"}],
        )

        loaded = load_revision_tasks("v0.1.0", "EPIC-001", "FEAT-001")
        assert loaded["feature_id"] == "FEAT-001"
        assert loaded["revision_round"] == 1
        assert loaded["trigger"] == "ac_validation"
        assert len(loaded["revision_tasks"]) == 1

    @patch("validators.revision_manager.PROJECT_ROOT", REVISIONS_DIR)
    def test_load_nonexistent_returns_empty(self):
        """load_revision_tasks returns empty dict for nonexistent file."""
        loaded = load_revision_tasks("v0.1.0", "EPIC-999", "FEAT-999")
        assert loaded == {}

    @patch("validators.revision_manager.PROJECT_ROOT", REVISIONS_DIR)
    def test_saved_json_is_valid(self):
        """Saved file contains valid JSON."""
        tasks = [{"id": "RT-1-001", "description": "Fix"}]
        save_revision_tasks(tasks, "v0.1.0", "EPIC-001", "FEAT-001")

        path = (
            REVISIONS_DIR
            / "project"
            / "v0.1.0"
            / "EPIC-001"
            / "FEAT-001"
            / "revisions"
            / "revision_tasks.json"
        )
        data = json.loads(path.read_text())
        assert "revision_tasks" in data
        assert "feature_id" in data


class TestInjectRevisionTasksIntoState:
    """Tests for inject_revision_tasks_into_state function."""

    def test_adds_tasks_to_current_tasks(self):
        """Injects revision tasks into current_tasks."""
        revision_tasks = [
            {"id": "RT-1-001", "status": "not_started"},
            {"id": "RT-1-002", "status": "not_started"},
        ]
        state = {"current_tasks": {"T001": "completed"}}

        result = inject_revision_tasks_into_state(revision_tasks, state)
        assert "RT-1-001" in result["current_tasks"]
        assert "RT-1-002" in result["current_tasks"]
        assert result["current_tasks"]["RT-1-001"] == "not_started"

    def test_preserves_existing_tasks(self):
        """Does not overwrite existing tasks in state."""
        revision_tasks = [{"id": "RT-1-001", "status": "not_started"}]
        state = {"current_tasks": {"T001": "completed", "T002": "in_progress"}}

        result = inject_revision_tasks_into_state(revision_tasks, state)
        assert result["current_tasks"]["T001"] == "completed"
        assert result["current_tasks"]["T002"] == "in_progress"

    def test_does_not_overwrite_existing_rt(self):
        """Does not overwrite existing revision tasks."""
        revision_tasks = [{"id": "RT-1-001", "status": "not_started"}]
        state = {"current_tasks": {"RT-1-001": "completed"}}

        result = inject_revision_tasks_into_state(revision_tasks, state)
        assert result["current_tasks"]["RT-1-001"] == "completed"

    def test_creates_current_tasks_if_missing(self):
        """Creates current_tasks dict if state has none."""
        revision_tasks = [{"id": "RT-1-001", "status": "not_started"}]
        state = {}

        result = inject_revision_tasks_into_state(revision_tasks, state)
        assert "current_tasks" in result
        assert "RT-1-001" in result["current_tasks"]

    def test_empty_revision_tasks_no_change(self):
        """Empty revision tasks list does not modify state."""
        state = {"current_tasks": {"T001": "completed"}}
        result = inject_revision_tasks_into_state([], state)
        assert result["current_tasks"] == {"T001": "completed"}


class TestGetNextRevisionRound:
    """Tests for get_next_revision_round function."""

    @patch("validators.revision_manager.PROJECT_ROOT", REVISIONS_DIR)
    def test_first_round_returns_1(self):
        """Returns 1 when no existing revisions."""
        result = get_next_revision_round("v0.1.0", "EPIC-001", "FEAT-001")
        assert result == 1

    @patch("validators.revision_manager.PROJECT_ROOT", REVISIONS_DIR)
    def test_increments_existing_round(self):
        """Returns current round + 1."""
        tasks = [{"id": "RT-1-001"}]
        save_revision_tasks(tasks, "v0.1.0", "EPIC-001", "FEAT-001", round_num=2)

        result = get_next_revision_round("v0.1.0", "EPIC-001", "FEAT-001")
        assert result == 3


class TestGetRevisionsPath:
    """Tests for _get_revisions_path helper."""

    def test_path_structure(self):
        """Path follows expected structure."""
        path = _get_revisions_path("v0.1.0", "EPIC-001", "FEAT-001")
        parts = path.parts
        assert "project" in parts
        assert "v0.1.0" in parts
        assert "EPIC-001" in parts
        assert "FEAT-001" in parts
        assert "revisions" in parts
        assert path.name == "revision_tasks.json"


class TestImports:
    """Tests for module imports."""

    def test_revision_manager_import(self):
        """All public functions can be imported."""
        from validators.revision_manager import (
            create_revision_tasks,
            save_revision_tasks,
            load_revision_tasks,
            inject_revision_tasks_into_state,
            get_next_revision_round,
        )

        assert callable(create_revision_tasks)
        assert callable(save_revision_tasks)
        assert callable(load_revision_tasks)
        assert callable(inject_revision_tasks_into_state)
        assert callable(get_next_revision_round)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
