"""Tests for guards/task_guard.py — PreToolUse TaskCreate + TaskCompleted."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow.guards import task_guard
from workflow.state_store import StateStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_TASKS_JSON = json.dumps([
    {
        "id": "T-017",
        "title": "Feature importance analysis documented in decisions.md",
        "description": "Perform feature importance analysis and document findings",
        "status": "Backlog",
    },
    {
        "id": "T-018",
        "title": "Recommendation includes feature set with pros/cons",
        "description": "Develop feature set recommendations with trade-offs",
        "status": "Ready",
    },
])


def make_state(phase: str = "task-create", **kwargs) -> dict:
    state = {
        "workflow_active": True,
        "workflow_type": "implement",
        "phase": phase,
        "story_id": kwargs.get("story_id", "SK-001"),
        "tasks_created": kwargs.get("tasks_created", 0),
    }
    if kwargs.get("tdd"):
        state["tdd"] = True
    return state


def make_state_with_tasks(phase: str = "task-create", **kwargs) -> dict:
    """State that already has cached tasks (skip subprocess)."""
    state = make_state(phase, **kwargs)
    state["tasks"] = kwargs.get("tasks", [
        {
            "id": "T-017",
            "subject": "Feature importance analysis documented in decisions.md",
            "description": "Perform feature importance analysis and document findings",
            "status": "pending",
            "subtasks": [],
        },
        {
            "id": "T-018",
            "subject": "Recommendation includes feature set with pros/cons",
            "description": "Develop feature set recommendations with trade-offs",
            "status": "pending",
            "subtasks": [],
        },
    ])
    return state


def write_state(tmp_state_file, state: dict) -> None:
    tmp_state_file.write_text(json.dumps(state))


def task_create_hook(
    subject: str,
    description: str = "Do the thing.",
    parent_task_id: str | None = None,
    parent_task_title: str | None = None,
    include_metadata: bool = True,
) -> dict:
    """Build PreToolUse TaskCreate hook input."""
    tool_input = {
        "subject": subject,
        "description": description,
    }
    if include_metadata:
        metadata = {}
        if parent_task_id is not None:
            metadata["parent_task_id"] = parent_task_id
        if parent_task_title is not None:
            metadata["parent_task_title"] = parent_task_title
        tool_input["metadata"] = metadata

    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "TaskCreate",
        "tool_input": tool_input,
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def task_completed_hook(subject: str, task_id: str = "task-001") -> dict:
    """Build TaskCompleted hook input."""
    return {
        "hook_event_name": "TaskCompleted",
        "task_id": task_id,
        "task_subject": subject,
        "task_description": "Do the thing.",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def _mock_subprocess_run():
    """Return a patch that mocks subprocess.run for project_manager calls."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = PROJECT_TASKS_JSON
    return patch.object(task_guard.subprocess, "run", return_value=mock_result)


# ---------------------------------------------------------------------------
# PreToolUse TaskCreate tests
# ---------------------------------------------------------------------------


class TestTaskGuardValidate:
    def test_workflow_inactive_allows_all(self, tmp_state_file):
        tmp_state_file.write_text("{}")
        store = StateStore(tmp_state_file)
        decision, _ = task_guard.validate(task_create_hook("Any subject"), store)
        assert decision == "allow"

    def test_outside_task_create_phase_allows_all(self, tmp_state_file):
        write_state(tmp_state_file, make_state(phase="write-code", story_id="SK-001"))
        store = StateStore(tmp_state_file)
        decision, _ = task_guard.validate(task_create_hook("Any subject"), store)
        assert decision == "allow"

    def test_no_story_id_allows_all(self, tmp_state_file):
        write_state(tmp_state_file, make_state(story_id=None))
        store = StateStore(tmp_state_file)
        decision, _ = task_guard.validate(task_create_hook("Any subject"), store)
        assert decision == "allow"

    def test_missing_metadata_blocked(self, tmp_state_file):
        write_state(tmp_state_file, make_state())
        store = StateStore(tmp_state_file)
        hook = task_create_hook("Implement login", include_metadata=False)
        decision, reason = task_guard.validate(hook, store)
        assert decision == "block"
        assert "metadata" in reason.lower()

    def test_missing_parent_task_id_blocked(self, tmp_state_file):
        write_state(tmp_state_file, make_state())
        store = StateStore(tmp_state_file)
        hook = task_create_hook(
            "Implement login",
            parent_task_id=None,
            parent_task_title="Some title",
        )
        decision, reason = task_guard.validate(hook, store)
        assert decision == "block"
        assert "parent_task_id" in reason

    def test_missing_parent_task_title_blocked(self, tmp_state_file):
        write_state(tmp_state_file, make_state())
        store = StateStore(tmp_state_file)
        hook = task_create_hook(
            "Implement login",
            parent_task_id="T-017",
            parent_task_title=None,
        )
        decision, reason = task_guard.validate(hook, store)
        assert decision == "block"
        assert "parent_task_title" in reason

    def test_valid_parent_task_allowed(self, tmp_state_file):
        write_state(tmp_state_file, make_state_with_tasks())
        store = StateStore(tmp_state_file)
        hook = task_create_hook(
            "Analyze feature correlations",
            parent_task_id="T-017",
            parent_task_title="Feature importance analysis documented in decisions.md",
        )
        decision, _ = task_guard.validate(hook, store)
        assert decision == "allow"

    def test_parent_task_id_not_in_project_blocked(self, tmp_state_file):
        write_state(tmp_state_file, make_state_with_tasks())
        store = StateStore(tmp_state_file)
        hook = task_create_hook(
            "Analyze something",
            parent_task_id="T-999",
            parent_task_title="Nonexistent task",
        )
        decision, reason = task_guard.validate(hook, store)
        assert decision == "block"
        assert "T-999" in reason

    def test_parent_task_title_mismatch_blocked(self, tmp_state_file):
        write_state(tmp_state_file, make_state_with_tasks())
        store = StateStore(tmp_state_file)
        hook = task_create_hook(
            "Analyze something",
            parent_task_id="T-017",
            parent_task_title="Wrong title here",
        )
        decision, reason = task_guard.validate(hook, store)
        assert decision == "block"
        assert "mismatch" in reason.lower()

    def test_subtask_recorded_on_allow(self, tmp_state_file):
        write_state(tmp_state_file, make_state_with_tasks())
        store = StateStore(tmp_state_file)
        hook = task_create_hook(
            "Analyze feature correlations",
            description="Run correlation analysis",
            parent_task_id="T-017",
            parent_task_title="Feature importance analysis documented in decisions.md",
        )
        task_guard.validate(hook, store)
        state = store.load()
        parent = next(t for t in state["tasks"] if t["id"] == "T-017")
        assert len(parent["subtasks"]) == 1
        assert parent["subtasks"][0]["subject"] == "Analyze feature correlations"
        assert parent["subtasks"][0]["description"] == "Run correlation analysis"
        assert parent["subtasks"][0]["status"] == "pending"
        assert parent["subtasks"][0]["id"] == 1

    def test_cache_populated_on_first_call(self, tmp_state_file):
        write_state(tmp_state_file, make_state())
        store = StateStore(tmp_state_file)
        hook = task_create_hook(
            "Analyze features",
            parent_task_id="T-017",
            parent_task_title="Feature importance analysis documented in decisions.md",
        )
        with _mock_subprocess_run() as mock_run:
            decision, _ = task_guard.validate(hook, store)

        assert decision == "allow"
        mock_run.assert_called_once()
        state = store.load()
        assert "tasks" in state
        assert len(state["tasks"]) == 2
        assert state["tasks"][0]["id"] == "T-017"

    def test_cache_reused_on_second_call(self, tmp_state_file):
        write_state(tmp_state_file, make_state_with_tasks())
        store = StateStore(tmp_state_file)
        hook = task_create_hook(
            "First task",
            parent_task_id="T-017",
            parent_task_title="Feature importance analysis documented in decisions.md",
        )
        with _mock_subprocess_run() as mock_run:
            task_guard.validate(hook, store)
            # Second call — cache should be reused
            hook2 = task_create_hook(
                "Second task",
                parent_task_id="T-018",
                parent_task_title="Recommendation includes feature set with pros/cons",
            )
            task_guard.validate(hook2, store)

        mock_run.assert_not_called()

    def test_auto_advance_to_write_code_when_all_tasks_covered(self, tmp_state_file):
        write_state(tmp_state_file, make_state_with_tasks())
        store = StateStore(tmp_state_file)
        # Cover first task
        task_guard.validate(task_create_hook(
            "Task for T-017",
            parent_task_id="T-017",
            parent_task_title="Feature importance analysis documented in decisions.md",
        ), store)
        state = store.load()
        assert state["phase"] == "task-create"  # not all covered yet

        # Cover second task — should auto-advance
        task_guard.validate(task_create_hook(
            "Task for T-018",
            parent_task_id="T-018",
            parent_task_title="Recommendation includes feature set with pros/cons",
        ), store)
        state = store.load()
        assert state["phase"] == "write-code"

    def test_auto_advance_to_write_tests_with_tdd(self, tmp_state_file):
        write_state(tmp_state_file, make_state_with_tasks(tdd=True))
        store = StateStore(tmp_state_file)
        task_guard.validate(task_create_hook(
            "Task for T-017",
            parent_task_id="T-017",
            parent_task_title="Feature importance analysis documented in decisions.md",
        ), store)
        task_guard.validate(task_create_hook(
            "Task for T-018",
            parent_task_id="T-018",
            parent_task_title="Recommendation includes feature set with pros/cons",
        ), store)
        state = store.load()
        assert state["phase"] == "write-tests"

    def test_no_advance_when_uncovered_tasks_remain(self, tmp_state_file):
        write_state(tmp_state_file, make_state_with_tasks())
        store = StateStore(tmp_state_file)
        task_guard.validate(task_create_hook(
            "Task for T-017",
            parent_task_id="T-017",
            parent_task_title="Feature importance analysis documented in decisions.md",
        ), store)
        state = store.load()
        assert state["phase"] == "task-create"


# ---------------------------------------------------------------------------
# TaskCompleted tests
# ---------------------------------------------------------------------------


class TestTaskGuardCompleted:
    def _state_with_subtasks(self) -> dict:
        """State with a parent task that has subtasks."""
        return {
            "workflow_active": True,
            "workflow_type": "implement",
            "phase": "write-code",
            "story_id": "SK-001",
            "tasks": [
                {
                    "id": "T-017",
                    "subject": "Feature importance analysis",
                    "description": "Perform analysis",
                    "status": "pending",
                    "subtasks": [
                        {"id": 1, "subject": "Analyze correlations", "description": "", "status": "pending"},
                        {"id": 2, "subject": "Rank top features", "description": "", "status": "pending"},
                    ],
                },
            ],
        }

    def test_task_completed_updates_subtask_status(self, tmp_state_file):
        write_state(tmp_state_file, self._state_with_subtasks())
        store = StateStore(tmp_state_file)
        hook = task_completed_hook("Analyze correlations")
        decision, _ = task_guard.validate_completed(hook, store)
        assert decision == "allow"
        state = store.load()
        subtask = state["tasks"][0]["subtasks"][0]
        assert subtask["status"] == "completed"

    def test_task_completed_no_match_allows(self, tmp_state_file):
        write_state(tmp_state_file, self._state_with_subtasks())
        store = StateStore(tmp_state_file)
        hook = task_completed_hook("Unknown task subject")
        decision, _ = task_guard.validate_completed(hook, store)
        assert decision == "allow"

    def test_task_completed_workflow_inactive_allows(self, tmp_state_file):
        tmp_state_file.write_text("{}")
        store = StateStore(tmp_state_file)
        hook = task_completed_hook("Any subject")
        decision, _ = task_guard.validate_completed(hook, store)
        assert decision == "allow"

    def test_all_subtasks_completed_resolves_parent(self, tmp_state_file):
        write_state(tmp_state_file, self._state_with_subtasks())
        store = StateStore(tmp_state_file)

        # Complete first subtask
        task_guard.validate_completed(task_completed_hook("Analyze correlations"), store)
        state = store.load()
        assert state["tasks"][0]["status"] == "pending"

        # Complete second subtask — parent should resolve
        task_guard.validate_completed(task_completed_hook("Rank top features"), store)
        state = store.load()
        assert state["tasks"][0]["status"] == "completed"

    def test_partial_subtasks_completed_parent_stays_pending(self, tmp_state_file):
        write_state(tmp_state_file, self._state_with_subtasks())
        store = StateStore(tmp_state_file)

        task_guard.validate_completed(task_completed_hook("Analyze correlations"), store)
        state = store.load()
        assert state["tasks"][0]["status"] == "pending"
        assert state["tasks"][0]["subtasks"][0]["status"] == "completed"
        assert state["tasks"][0]["subtasks"][1]["status"] == "pending"
