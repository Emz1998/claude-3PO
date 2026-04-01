"""Tests for guards/task_guard.py."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow.guards import task_guard
from workflow.state_store import StateStore


def make_state(phase: str = "task-create", **kwargs) -> dict:
    return {
        "workflow_active": True,
        "workflow_type": "implement",
        "phase": phase,
        "story_id": kwargs.get("story_id", "SK-123"),
        "tasks_created": kwargs.get("tasks_created", 0),
    }


def write_state(tmp_state_file, state: dict) -> None:
    tmp_state_file.write_text(json.dumps(state))


def task_created_hook(subject: str, task_id: str = "1", description: str = "") -> dict:
    return {
        "hook_event_name": "TaskCreated",
        "task_id": task_id,
        "task_subject": subject,
        "task_description": description,
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


class TestTaskGuard:
    def test_valid_subject_with_story_prefix_allowed(self, tmp_state_file):
        write_state(tmp_state_file, make_state(story_id="SK-123"))
        store = StateStore(tmp_state_file)
        decision, _ = task_guard.validate(task_created_hook("SK-123: Implement login"), store)
        assert decision == "allow"

    def test_invalid_subject_without_story_prefix_blocked(self, tmp_state_file):
        write_state(tmp_state_file, make_state(story_id="SK-123"))
        store = StateStore(tmp_state_file)
        decision, reason = task_guard.validate(task_created_hook("Implement login"), store)
        assert decision == "block"
        assert "SK-123" in reason or "prefix" in reason.lower() or "format" in reason.lower()

    def test_task_count_incremented_on_allow(self, tmp_state_file):
        write_state(tmp_state_file, make_state(story_id="SK-123", tasks_created=0))
        store = StateStore(tmp_state_file)
        task_guard.validate(task_created_hook("SK-123: Implement feature"), store)
        state = store.load()
        assert state["tasks_created"] == 1

    def test_no_story_id_allows_any_subject(self, tmp_state_file):
        write_state(tmp_state_file, make_state(story_id=None))
        store = StateStore(tmp_state_file)
        decision, _ = task_guard.validate(task_created_hook("Implement login"), store)
        assert decision == "allow"

    def test_workflow_inactive_allows_all(self, tmp_state_file):
        tmp_state_file.write_text("{}")
        store = StateStore(tmp_state_file)
        decision, _ = task_guard.validate(task_created_hook("Any subject"), store)
        assert decision == "allow"

    def test_wrong_story_id_prefix_blocked(self, tmp_state_file):
        write_state(tmp_state_file, make_state(story_id="SK-456"))
        store = StateStore(tmp_state_file)
        decision, reason = task_guard.validate(task_created_hook("SK-123: Wrong story"), store)
        assert decision == "block"

    def test_outside_task_create_phase_allows_all(self, tmp_state_file):
        write_state(tmp_state_file, make_state(phase="write-code", story_id="SK-123"))
        store = StateStore(tmp_state_file)
        decision, _ = task_guard.validate(task_created_hook("Any subject"), store)
        assert decision == "allow"
