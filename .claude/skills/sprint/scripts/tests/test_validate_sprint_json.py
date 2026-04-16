"""Tests for validate_sprint_json.py"""

import json
from pathlib import Path
from copy import deepcopy

import pytest

from validate_sprint_json import validate

SAMPLE_JSON = Path(__file__).resolve().parent.parent.parent / "sample_structure.json"


@pytest.fixture
def valid_data() -> dict:
    return json.loads(SAMPLE_JSON.read_text())


# ── Root-level validation ────────────────────────────────────────────────────


class TestRootValidation:
    def test_valid_data_has_no_errors(self, valid_data):
        assert validate(valid_data) == []

    def test_missing_sprint_field(self, valid_data):
        del valid_data["sprint"]
        errors = validate(valid_data)
        assert any("'sprint'" in e for e in errors)

    def test_missing_milestone(self, valid_data):
        del valid_data["milestone"]
        errors = validate(valid_data)
        assert any("'milestone'" in e for e in errors)

    def test_missing_description(self, valid_data):
        del valid_data["description"]
        errors = validate(valid_data)
        assert any("'description'" in e for e in errors)

    def test_missing_due_date(self, valid_data):
        del valid_data["due_date"]
        errors = validate(valid_data)
        assert any("'due_date'" in e for e in errors)

    def test_missing_stories(self, valid_data):
        del valid_data["stories"]
        errors = validate(valid_data)
        assert any("'stories'" in e for e in errors)

    def test_stories_not_a_list(self, valid_data):
        valid_data["stories"] = "not a list"
        errors = validate(valid_data)
        assert any("expected array" in e for e in errors)

    def test_invalid_due_date_format(self, valid_data):
        valid_data["due_date"] = "March 2026"
        errors = validate(valid_data)
        assert any("YYYY-MM-DD" in e for e in errors)

    def test_wrong_type_sprint(self, valid_data):
        valid_data["sprint"] = "one"
        errors = validate(valid_data)
        assert any("expected int" in e for e in errors)


# ── Story-level validation ───────────────────────────────────────────────────


class TestStoryValidation:
    def test_invalid_story_type(self, valid_data):
        valid_data["stories"][0]["type"] = "Epic"
        errors = validate(valid_data)
        assert any("'Epic'" in e for e in errors)

    def test_mismatched_id_pattern(self, valid_data):
        valid_data["stories"][0]["type"] = "Bug"
        valid_data["stories"][0]["id"] = "SK-001"
        errors = validate(valid_data)
        assert any("does not match pattern" in e for e in errors)

    def test_invalid_story_status(self, valid_data):
        valid_data["stories"][0]["status"] = "Pending"
        errors = validate(valid_data)
        assert any("'Pending'" in e for e in errors)

    def test_invalid_priority(self, valid_data):
        valid_data["stories"][0]["priority"] = "P9"
        errors = validate(valid_data)
        assert any("'P9'" in e for e in errors)

    def test_missing_tasks_array(self, valid_data):
        del valid_data["stories"][0]["tasks"]
        errors = validate(valid_data)
        assert any("'tasks'" in e for e in errors)

    def test_wrong_item_type(self, valid_data):
        valid_data["stories"][0]["item_type"] = "task"
        errors = validate(valid_data)
        assert any("must be 'story'" in e for e in errors)

    def test_missing_required_list_field(self, valid_data):
        del valid_data["stories"][0]["labels"]
        errors = validate(valid_data)
        assert any("'labels'" in e for e in errors)

    def test_invalid_start_date_format(self, valid_data):
        valid_data["stories"][0]["start_date"] = "Feb 17"
        errors = validate(valid_data)
        assert any("start_date" in e and "YYYY-MM-DD" in e for e in errors)

    def test_empty_dates_are_valid(self, valid_data):
        valid_data["stories"][0]["start_date"] = ""
        valid_data["stories"][0]["target_date"] = ""
        errors = validate(valid_data)
        date_errors = [e for e in errors if "date" in e.lower() and "stories[0]." in e]
        assert date_errors == []

    def test_non_dict_story_is_flagged(self, valid_data):
        valid_data["stories"].append("not a dict")
        errors = validate(valid_data)
        assert any("expected object" in e for e in errors)


# ── Task-level validation ────────────────────────────────────────────────────


class TestTaskValidation:
    def _get_task(self, data, story_idx=0, task_idx=0):
        return data["stories"][story_idx]["tasks"][task_idx]

    def test_invalid_task_id_pattern(self, valid_data):
        self._get_task(valid_data)["id"] = "TASK-1"
        errors = validate(valid_data)
        assert any("T-NNN" in e for e in errors)

    def test_invalid_task_status(self, valid_data):
        self._get_task(valid_data)["status"] = "Waiting"
        errors = validate(valid_data)
        assert any("'Waiting'" in e for e in errors)

    def test_invalid_task_priority(self, valid_data):
        self._get_task(valid_data)["priority"] = "P5"
        errors = validate(valid_data)
        assert any("'P5'" in e for e in errors)

    def test_invalid_task_complexity(self, valid_data):
        self._get_task(valid_data)["complexity"] = "XL"
        errors = validate(valid_data)
        assert any("'XL'" in e for e in errors)

    def test_wrong_task_type_field(self, valid_data):
        self._get_task(valid_data)["type"] = "story"
        errors = validate(valid_data)
        assert any("must be 'task'" in e for e in errors)

    def test_wrong_task_item_type(self, valid_data):
        self._get_task(valid_data)["item_type"] = "story"
        errors = validate(valid_data)
        assert any("must be 'task'" in e for e in errors)

    def test_unknown_blocked_by_ref(self, valid_data):
        self._get_task(valid_data)["blocked_by"] = ["T-999"]
        errors = validate(valid_data)
        assert any("unknown ID" in e for e in errors)

    def test_unknown_is_blocking_ref(self, valid_data):
        self._get_task(valid_data)["is_blocking"] = ["T-999"]
        errors = validate(valid_data)
        assert any("unknown ID" in e for e in errors)

    def test_valid_blocked_by_ref(self, valid_data):
        """References to real task IDs should not produce errors."""
        tasks = valid_data["stories"][0]["tasks"]
        if len(tasks) >= 2:
            tasks[1]["blocked_by"] = [tasks[0]["id"]]
        errors = validate(valid_data)
        ref_errors = [e for e in errors if "unknown ID" in e]
        assert ref_errors == []

    def test_non_dict_task_is_flagged(self, valid_data):
        valid_data["stories"][0]["tasks"].append("not a dict")
        errors = validate(valid_data)
        assert any("expected object" in e for e in errors)

    def test_missing_task_fields(self, valid_data):
        task = self._get_task(valid_data)
        del task["title"]
        del task["status"]
        errors = validate(valid_data)
        assert any("'title'" in e for e in errors)
        assert any("'status'" in e for e in errors)


# ── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_stories_list(self, valid_data):
        valid_data["stories"] = []
        errors = validate(valid_data)
        assert errors == []

    def test_minimal_valid_structure(self):
        data = {
            "sprint": 1,
            "milestone": "v1",
            "description": "test",
            "due_date": "2026-01-01",
            "stories": [],
        }
        assert validate(data) == []
