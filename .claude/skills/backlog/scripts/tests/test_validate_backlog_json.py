"""Tests for validate_backlog_json.py"""

import json
from pathlib import Path
from copy import deepcopy

import pytest

from validate_backlog_json import validate

SAMPLE_JSON = Path(__file__).resolve().parent.parent.parent / "sample_structure.json"


@pytest.fixture
def valid_data() -> dict:
    return json.loads(SAMPLE_JSON.read_text())


# ── Root-level validation ────────────────────────────────────────────────────


class TestRootValidation:
    def test_valid_data_has_no_errors(self, valid_data):
        assert validate(valid_data) == []

    def test_missing_project(self, valid_data):
        del valid_data["project"]
        errors = validate(valid_data)
        assert any("'project'" in e for e in errors)

    def test_missing_goal(self, valid_data):
        del valid_data["goal"]
        errors = validate(valid_data)
        assert any("'goal'" in e for e in errors)

    def test_missing_dates(self, valid_data):
        del valid_data["dates"]
        errors = validate(valid_data)
        assert any("'dates'" in e for e in errors)

    def test_dates_not_a_dict(self, valid_data):
        valid_data["dates"] = "not a dict"
        errors = validate(valid_data)
        assert any("expected object" in e for e in errors)

    def test_missing_dates_start(self, valid_data):
        del valid_data["dates"]["start"]
        errors = validate(valid_data)
        assert any("'start'" in e for e in errors)

    def test_missing_dates_end(self, valid_data):
        del valid_data["dates"]["end"]
        errors = validate(valid_data)
        assert any("'end'" in e for e in errors)

    def test_invalid_date_format(self, valid_data):
        valid_data["dates"]["start"] = "March 2026"
        errors = validate(valid_data)
        assert any("YYYY-MM-DD" in e for e in errors)

    def test_empty_dates_are_valid(self, valid_data):
        valid_data["dates"]["start"] = ""
        valid_data["dates"]["end"] = ""
        errors = validate(valid_data)
        date_errors = [e for e in errors if "dates" in e]
        assert date_errors == []

    def test_missing_total_points(self, valid_data):
        del valid_data["totalPoints"]
        errors = validate(valid_data)
        assert any("'totalPoints'" in e for e in errors)

    def test_total_points_wrong_type(self, valid_data):
        valid_data["totalPoints"] = "twenty"
        errors = validate(valid_data)
        assert any("expected int" in e for e in errors)

    def test_missing_stories(self, valid_data):
        del valid_data["stories"]
        errors = validate(valid_data)
        assert any("'stories'" in e for e in errors)

    def test_stories_not_a_list(self, valid_data):
        valid_data["stories"] = "not a list"
        errors = validate(valid_data)
        assert any("expected array" in e for e in errors)


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

    def test_invalid_status(self, valid_data):
        valid_data["stories"][0]["status"] = "Pending"
        errors = validate(valid_data)
        assert any("'Pending'" in e for e in errors)

    def test_invalid_priority(self, valid_data):
        valid_data["stories"][0]["priority"] = "P9"
        errors = validate(valid_data)
        assert any("'P9'" in e for e in errors)

    def test_wrong_item_type(self, valid_data):
        valid_data["stories"][0]["item_type"] = "task"
        errors = validate(valid_data)
        assert any("must be 'story'" in e for e in errors)

    def test_missing_item_type(self, valid_data):
        del valid_data["stories"][0]["item_type"]
        errors = validate(valid_data)
        assert any("'item_type'" in e for e in errors)

    def test_missing_required_string_field(self, valid_data):
        del valid_data["stories"][0]["title"]
        errors = validate(valid_data)
        assert any("'title'" in e for e in errors)

    def test_missing_required_list_field(self, valid_data):
        del valid_data["stories"][0]["is_blocking"]
        errors = validate(valid_data)
        assert any("'is_blocking'" in e for e in errors)

    def test_invalid_start_date_format(self, valid_data):
        valid_data["stories"][0]["start_date"] = "Feb 17"
        errors = validate(valid_data)
        assert any("start_date" in e and "YYYY-MM-DD" in e for e in errors)

    def test_invalid_target_date_format(self, valid_data):
        valid_data["stories"][0]["target_date"] = "Feb 28"
        errors = validate(valid_data)
        assert any("target_date" in e and "YYYY-MM-DD" in e for e in errors)

    def test_empty_dates_are_valid(self, valid_data):
        valid_data["stories"][0]["start_date"] = ""
        valid_data["stories"][0]["target_date"] = ""
        errors = validate(valid_data)
        date_errors = [e for e in errors if "date" in e and "stories[0]." in e]
        assert date_errors == []

    def test_non_dict_story_is_flagged(self, valid_data):
        valid_data["stories"].append("not a dict")
        errors = validate(valid_data)
        assert any("expected object" in e for e in errors)


# ── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_stories_list(self, valid_data):
        valid_data["stories"] = []
        errors = validate(valid_data)
        assert errors == []

    def test_minimal_valid_structure(self):
        data = {
            "project": "Test",
            "goal": "Test goal",
            "dates": {"start": "", "end": ""},
            "totalPoints": 0,
            "stories": [],
        }
        assert validate(data) == []

    def test_wrong_type_for_string_field(self, valid_data):
        valid_data["stories"][0]["description"] = 123
        errors = validate(valid_data)
        assert any("expected str" in e for e in errors)

    def test_list_field_with_wrong_item_type(self, valid_data):
        valid_data["stories"][0]["acceptance_criteria"] = [123, 456]
        errors = validate(valid_data)
        assert any("must be str" in e for e in errors)
