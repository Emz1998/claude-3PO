"""Tests for project_manager.py — pure logic tests, no API calls."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent dir so we can import the module directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import project_manager as pm


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_RAW_ITEMS = [
    {
        "id": "ITEM-1",
        "title": "TS-001: Setup CI pipeline",
        "status": "In progress",
        "priority": "P0",
        "points": 5,
        "complexity": "",
        "type": "Tech",
        "start date": "2026-01-01",
        "target date": "2026-01-15",
        "labels": ["infra"],
        "assignees": ["alice"],
        "milestone": "Sprint 1",
        "content": {
            "type": "Issue",
            "number": 1,
            "body": "Set up CI",
            "url": "https://github.com/org/repo/issues/1",
        },
    },
    {
        "id": "ITEM-2",
        "title": "TS-002: Add auth module",
        "status": "Ready",
        "priority": "P1",
        "points": 8,
        "complexity": "",
        "type": "Tech",
        "start date": "",
        "target date": "",
        "labels": ["feature", "auth"],
        "assignees": ["bob"],
        "milestone": "Sprint 2",
        "content": {
            "type": "Issue",
            "number": 2,
            "body": "Implement auth",
            "url": "https://github.com/org/repo/issues/2",
        },
    },
    {
        "id": "ITEM-3",
        "title": "TS-003: Fix login bug",
        "status": "Done",
        "priority": "P0",
        "complexity": "S",
        "points": "",
        "type": "task",
        "start date": "2026-01-02",
        "target date": "2026-01-05",
        "labels": ["bug"],
        "assignees": ["alice"],
        "milestone": "Sprint 1",
        "content": {
            "type": "Issue",
            "number": 3,
            "body": "Login broken",
            "url": "https://github.com/org/repo/issues/3",
        },
    },
    {
        "id": "ITEM-PR",
        "title": "Some PR title",
        "content": {"type": "PullRequest", "number": 10},
    },
]


@pytest.fixture
def tasks():
    return pm.normalize_items(SAMPLE_RAW_ITEMS)


def _make_list_args(**overrides):
    defaults = dict(
        status=None, priority=None, milestone=None, assignee=None,
        label=None, complexity=None, type=None, sort_by=None, reverse=False,
        wide=False, keys_only=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_view_args(**overrides):
    defaults = dict(key="TS-001", raw=False, template=None)
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_summary_args(**overrides):
    defaults = dict(group_by="status")
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# _parse_key_title (colon format)
# ---------------------------------------------------------------------------


class TestParseKeyTitle:
    def test_colon_format(self):
        assert pm._parse_key_title("SK-001: Some title") == ("SK-001", "Some title")

    def test_without_key(self):
        assert pm._parse_key_title("Some title without key") == ("", "Some title without key")

    def test_multi_word_key(self):
        assert pm._parse_key_title("ABC-999: Multi word title") == ("ABC-999", "Multi word title")

    def test_empty_string(self):
        assert pm._parse_key_title("") == ("", "")


# ---------------------------------------------------------------------------
# normalize_items
# ---------------------------------------------------------------------------


class TestNormalizeItems:
    def test_filters_non_issues(self, tasks):
        # PR item should be filtered out
        assert len(tasks) == 3

    def test_parses_key_and_title(self, tasks):
        assert tasks[0]["key"] == "TS-001"
        assert tasks[0]["title"] == "Setup CI pipeline"

    def test_extracts_fields(self, tasks):
        t = tasks[0]
        assert t["status"] == "In progress"
        assert t["priority"] == "P0"
        assert t["issue_number"] == 1
        assert t["milestone"] == "Sprint 1"
        assert t["labels"] == ["infra"]
        assert t["assignees"] == ["alice"]

    def test_includes_points(self, tasks):
        assert tasks[0]["points"] == 5

    def test_includes_complexity(self, tasks):
        assert tasks[2]["complexity"] == "S"

    def test_includes_type(self, tasks):
        assert tasks[0]["type"] == "Tech"
        assert tasks[2]["type"] == "task"

    def test_milestone_dict(self):
        items = [{
            "title": "TS-010: Test",
            "milestone": {"title": "v1.0"},
            "content": {"type": "Issue", "number": 10},
        }]
        tasks = pm.normalize_items(items)
        assert tasks[0]["milestone"] == "v1.0"

    def test_empty_items(self):
        assert pm.normalize_items([]) == []


# ---------------------------------------------------------------------------
# flatten_v2_for_display
# ---------------------------------------------------------------------------


SAMPLE_V2_DATA = {
    "project": "Test",
    "milestone": "v0.1",
    "stories": [
        {
            "id": "SK-001",
            "type": "Spike",
            "title": "Research",
            "points": 3,
            "status": "In progress",
            "priority": "P0",
            "issue_number": 101,
            "tasks": [
                {
                    "id": "T-001",
                    "type": "task",
                    "title": "Analyze",
                    "complexity": "M",
                    "status": "Ready",
                    "priority": "P1",
                    "issue_number": 201,
                },
            ],
        },
    ],
}


class TestFlattenV2ForDisplay:
    def test_flattens_stories_and_tasks(self):
        result = pm.flatten_v2_for_display(SAMPLE_V2_DATA)
        assert len(result) == 2

    def test_story_has_points_no_complexity(self):
        result = pm.flatten_v2_for_display(SAMPLE_V2_DATA)
        story = [r for r in result if r["key"] == "SK-001"][0]
        assert story["points"] == 3
        assert story["complexity"] == ""

    def test_task_has_complexity_no_points(self):
        result = pm.flatten_v2_for_display(SAMPLE_V2_DATA)
        task = [r for r in result if r["key"] == "T-001"][0]
        assert task["complexity"] == "M"
        assert task["points"] == ""

    def test_task_has_parent_id(self):
        result = pm.flatten_v2_for_display(SAMPLE_V2_DATA)
        task = [r for r in result if r["key"] == "T-001"][0]
        assert task["parent_id"] == "SK-001"


# ---------------------------------------------------------------------------
# _sort_key
# ---------------------------------------------------------------------------


class TestSortKey:
    def test_priority_order(self):
        assert pm._sort_key("priority", {"priority": "P0"}) == 0
        assert pm._sort_key("priority", {"priority": "P3"}) == 3
        assert pm._sort_key("priority", {"priority": "Unknown"}) == 99

    def test_status_order(self):
        assert pm._sort_key("status", {"status": "Done"}) == 0
        assert pm._sort_key("status", {"status": "Backlog"}) == 3

    def test_complexity_order(self):
        assert pm._sort_key("complexity", {"complexity": "XS"}) == 0
        assert pm._sort_key("complexity", {"complexity": "XL"}) == 4

    def test_numeric_field(self):
        assert pm._sort_key("points", {"points": 5}) == 5
        assert pm._sort_key("points", {"points": None}) == 0

    def test_string_field(self):
        assert pm._sort_key("title", {"title": "Hello"}) == "hello"

    def test_none_value(self):
        assert pm._sort_key("priority", {"priority": None}) == 99


# ---------------------------------------------------------------------------
# _matches
# ---------------------------------------------------------------------------


class TestMatches:
    def test_exact_match(self):
        task = {"status": "Done", "priority": "P0"}
        assert pm._matches(task, {"status": "Done"}) is True
        assert pm._matches(task, {"status": "Ready"}) is False

    def test_case_insensitive(self):
        task = {"status": "In progress"}
        assert pm._matches(task, {"status": "in progress"}) is True

    def test_list_field(self):
        task = {"labels": ["bug", "feature"]}
        assert pm._matches(task, {"labels": "bug"}) is True
        assert pm._matches(task, {"labels": "docs"}) is False

    def test_missing_field(self):
        assert pm._matches({}, {"status": "Done"}) is False

    def test_multiple_filters(self):
        task = {"status": "Done", "priority": "P0"}
        assert pm._matches(task, {"status": "Done", "priority": "P0"}) is True
        assert pm._matches(task, {"status": "Done", "priority": "P1"}) is False

    def test_empty_filters(self):
        assert pm._matches({"status": "Done"}, {}) is True


# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------


class TestTruncate:
    def test_short_string(self):
        assert pm._truncate("hello", 10) == "hello"

    def test_exact_width(self):
        assert pm._truncate("hello", 5) == "hello"

    def test_long_string(self):
        result = pm._truncate("hello world", 6)
        assert result == "hello\u2026"
        assert len(result) == 6


# ---------------------------------------------------------------------------
# _find_task
# ---------------------------------------------------------------------------


class TestFindTask:
    def test_find_by_key(self, tasks):
        assert pm._find_task(tasks, "TS-001")["title"] == "Setup CI pipeline"

    def test_find_by_key_case_insensitive(self, tasks):
        assert pm._find_task(tasks, "ts-001")["title"] == "Setup CI pipeline"

    def test_find_by_issue_number(self, tasks):
        assert pm._find_task(tasks, "2")["key"] == "TS-002"

    def test_not_found(self, tasks):
        assert pm._find_task(tasks, "TS-999") is None


# ---------------------------------------------------------------------------
# _format_list
# ---------------------------------------------------------------------------


class TestFormatList:
    def test_list(self):
        assert pm._format_list(["a", "b"]) == "a, b"

    def test_empty_list(self):
        assert pm._format_list([]) == "(none)"

    def test_none(self):
        assert pm._format_list(None) == "(none)"

    def test_empty_string(self):
        assert pm._format_list("") == "(none)"

    def test_value(self):
        assert pm._format_list("hello") == "hello"


# ---------------------------------------------------------------------------
# _find_item_id
# ---------------------------------------------------------------------------


class TestFindItemId:
    def test_found(self):
        items = [
            {"id": "item-1", "content": {"number": 5}},
            {"id": "item-2", "content": {"number": 10}},
        ]
        assert pm._find_item_id(items, 10) == "item-2"

    def test_not_found(self):
        items = [{"id": "item-1", "content": {"number": 5}}]
        assert pm._find_item_id(items, 99) is None

    def test_empty_items(self):
        assert pm._find_item_id([], 1) is None


# ---------------------------------------------------------------------------
# cmd_list
# ---------------------------------------------------------------------------


class TestCmdList:
    def test_list_all(self, tasks, capsys):
        args = _make_list_args()
        assert pm.cmd_list(tasks, args) == 0
        out = capsys.readouterr().out
        assert "TS-001" in out
        assert "TS-002" in out
        assert "3 task(s)" in out

    def test_filter_by_status(self, tasks, capsys):
        args = _make_list_args(status="Done")
        pm.cmd_list(tasks, args)
        out = capsys.readouterr().out
        assert "TS-003" in out
        assert "1 task(s)" in out

    def test_filter_by_priority(self, tasks, capsys):
        args = _make_list_args(priority="P0")
        pm.cmd_list(tasks, args)
        out = capsys.readouterr().out
        assert "TS-001" in out
        assert "TS-003" in out
        assert "2 task(s)" in out

    def test_filter_by_milestone(self, tasks, capsys):
        args = _make_list_args(milestone="Sprint 2")
        pm.cmd_list(tasks, args)
        out = capsys.readouterr().out
        assert "TS-002" in out
        assert "1 task(s)" in out

    def test_sort_by_priority(self, tasks, capsys):
        args = _make_list_args(sort_by="priority")
        pm.cmd_list(tasks, args)
        out = capsys.readouterr().out
        lines = [l for l in out.strip().split("\n") if "TS-" in l]
        # P0 tasks first, then P1
        assert "TS-001" in lines[0] or "TS-003" in lines[0]
        assert "TS-002" in lines[2]

    def test_sort_reverse(self, tasks, capsys):
        args = _make_list_args(sort_by="priority", reverse=True)
        pm.cmd_list(tasks, args)
        out = capsys.readouterr().out
        lines = [l for l in out.strip().split("\n") if "TS-" in l]
        assert "TS-002" in lines[0]

    def test_keys_only(self, tasks, capsys):
        args = _make_list_args(keys_only=True)
        pm.cmd_list(tasks, args)
        out = capsys.readouterr().out.strip()
        assert out == "TS-001,TS-002,TS-003"

    def test_keys_only_with_filter(self, tasks, capsys):
        args = _make_list_args(keys_only=True, status="Done")
        pm.cmd_list(tasks, args)
        out = capsys.readouterr().out.strip()
        assert out == "TS-003"

    def test_wide_columns(self, tasks, capsys):
        args = _make_list_args(wide=True)
        pm.cmd_list(tasks, args)
        out = capsys.readouterr().out
        assert "START" in out
        assert "TARGET" in out
        assert "ASSIGNEES" in out

    def test_filter_by_label(self, tasks, capsys):
        args = _make_list_args(label="bug")
        pm.cmd_list(tasks, args)
        out = capsys.readouterr().out
        assert "TS-003" in out
        assert "1 task(s)" in out

    def test_filter_by_complexity(self, tasks, capsys):
        args = _make_list_args(complexity="S")
        pm.cmd_list(tasks, args)
        out = capsys.readouterr().out
        assert "TS-003" in out
        assert "1 task(s)" in out

    def test_filter_by_assignee(self, tasks, capsys):
        args = _make_list_args(assignee="bob")
        pm.cmd_list(tasks, args)
        out = capsys.readouterr().out
        assert "TS-002" in out
        assert "1 task(s)" in out

    def test_filter_by_type(self, tasks, capsys):
        args = _make_list_args(type="task")
        pm.cmd_list(tasks, args)
        out = capsys.readouterr().out
        assert "TS-003" in out
        assert "1 task(s)" in out


# ---------------------------------------------------------------------------
# cmd_view
# ---------------------------------------------------------------------------


class TestCmdView:
    def test_view_raw(self, tasks, capsys):
        args = _make_view_args(key="TS-001", raw=True)
        assert pm.cmd_view(tasks, args) == 0
        out = capsys.readouterr().out
        assert "Setup CI pipeline" in out
        assert "In progress" in out

    def test_view_not_found(self, tasks, capsys):
        args = _make_view_args(key="TS-999")
        assert pm.cmd_view(tasks, args) == 1

    def test_view_by_issue_number(self, tasks, capsys):
        args = _make_view_args(key="2", raw=True)
        assert pm.cmd_view(tasks, args) == 0
        out = capsys.readouterr().out
        assert "Add auth module" in out


# ---------------------------------------------------------------------------
# cmd_summary
# ---------------------------------------------------------------------------


class TestCmdSummary:
    def test_summary_by_status(self, tasks, capsys):
        args = _make_summary_args(group_by="status")
        assert pm.cmd_summary(tasks, args) == 0
        out = capsys.readouterr().out
        assert "Summary by status" in out
        assert "3 tasks" in out
        assert "Done" in out
        assert "In progress" in out
        assert "Ready" in out

    def test_summary_by_priority(self, tasks, capsys):
        args = _make_summary_args(group_by="priority")
        assert pm.cmd_summary(tasks, args) == 0
        out = capsys.readouterr().out
        assert "Summary by priority" in out
        assert "P0" in out
        assert "P1" in out

    def test_summary_by_milestone(self, tasks, capsys):
        args = _make_summary_args(group_by="milestone")
        assert pm.cmd_summary(tasks, args) == 0
        out = capsys.readouterr().out
        assert "Sprint 1" in out
        assert "Sprint 2" in out


# ---------------------------------------------------------------------------
# cmd_update (mocked API calls)
# ---------------------------------------------------------------------------


class TestCmdUpdate:
    def _make_update_args(self, **overrides):
        defaults = dict(
            key="TS-001", project=4, owner="testowner", repo="testowner/testrepo",
            status=None, priority=None, complexity=None, points=None,
            milestone=None, title=None, start_date=None, target_date=None,
            add_label=None, remove_label=None, add_assignee=None, remove_assignee=None,
            issues_data=None,
        )
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    def test_nothing_to_update(self, capsys):
        args = self._make_update_args()
        assert pm.cmd_update([], args) == 1
        assert "Nothing to update" in capsys.readouterr().err

    def test_missing_project(self, capsys):
        args = self._make_update_args(project=None, status="Done")
        assert pm.cmd_update([], args) == 1

    def test_missing_repo(self, capsys):
        args = self._make_update_args(repo=None, milestone="Sprint 1")
        assert pm.cmd_update([], args) == 1

    @patch.object(pm, "fetch_project_items", return_value=SAMPLE_RAW_ITEMS)
    @patch.object(pm, "_get_project_id", return_value="PID-123")
    @patch.object(pm, "_get_project_fields", return_value={
        "Status": {"id": "F1", "options": {"In progress": "OPT1", "Done": "OPT2"}},
    })
    @patch.object(pm, "_run", return_value="")
    def test_update_status(self, mock_run, mock_fields, mock_pid, mock_items, capsys):
        args = self._make_update_args(status="Done")
        assert pm.cmd_update([], args) == 0
        out = capsys.readouterr().out
        assert "Set Status = Done" in out

    @patch.object(pm, "fetch_project_items", return_value=SAMPLE_RAW_ITEMS)
    @patch.object(pm, "_get_project_id", return_value="PID-123")
    @patch.object(pm, "_get_project_fields", return_value={})
    @patch.object(pm, "_run", return_value="")
    def test_update_milestone(self, mock_run, mock_fields, mock_pid, mock_items, capsys):
        args = self._make_update_args(milestone="Sprint 3")
        assert pm.cmd_update([], args) == 0
        out = capsys.readouterr().out
        assert "Updated issue #1" in out
        # Verify gh issue edit was called with --milestone
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "--milestone" in call_args
        assert "Sprint 3" in call_args

    @patch.object(pm, "fetch_project_items", return_value=SAMPLE_RAW_ITEMS)
    @patch.object(pm, "_get_project_id", return_value="PID-123")
    @patch.object(pm, "_get_project_fields", return_value={})
    @patch.object(pm, "_run", return_value="")
    def test_update_labels(self, mock_run, mock_fields, mock_pid, mock_items, capsys):
        args = self._make_update_args(add_label=["bug", "urgent"], remove_label=["infra"])
        assert pm.cmd_update([], args) == 0
        call_args = mock_run.call_args[0][0]
        assert "--add-label" in call_args
        assert "bug" in call_args
        assert "urgent" in call_args
        assert "--remove-label" in call_args

    @patch.object(pm, "fetch_project_items", return_value=SAMPLE_RAW_ITEMS)
    @patch.object(pm, "_get_project_id", return_value="PID-123")
    @patch.object(pm, "_get_project_fields", return_value={})
    def test_update_task_not_found(self, mock_fields, mock_pid, mock_items, capsys):
        args = self._make_update_args(key="TS-999", status="Done")
        assert pm.cmd_update([], args) == 1
        assert "Task not found" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# _set_project_field
# ---------------------------------------------------------------------------


class TestSetProjectField:
    @patch.object(pm, "_run", return_value="")
    def test_single_select(self, mock_run):
        field_map = {
            "Status": {"id": "F1", "options": {"Done": "OPT1", "Ready": "OPT2"}},
        }
        assert pm._set_project_field("PID", "ITEM", field_map, "Status", "Done") is True
        call_args = mock_run.call_args[0][0]
        assert "--single-select-option-id" in call_args
        assert "OPT1" in call_args

    @patch.object(pm, "_run", return_value="")
    def test_number_value(self, mock_run):
        field_map = {"Points": {"id": "F2"}}
        assert pm._set_project_field("PID", "ITEM", field_map, "Points", 5) is True
        call_args = mock_run.call_args[0][0]
        assert "--number" in call_args
        assert "5" in call_args

    @patch.object(pm, "_run", return_value="")
    def test_date_value(self, mock_run):
        field_map = {"Start date": {"id": "F3"}}
        assert pm._set_project_field("PID", "ITEM", field_map, "Start date", "2026-01-01") is True
        call_args = mock_run.call_args[0][0]
        assert "--date" in call_args

    @patch.object(pm, "_run", return_value="")
    def test_text_value(self, mock_run):
        field_map = {"Notes": {"id": "F4"}}
        assert pm._set_project_field("PID", "ITEM", field_map, "Notes", "hello") is True
        call_args = mock_run.call_args[0][0]
        assert "--text" in call_args

    def test_field_not_found(self, capsys):
        assert pm._set_project_field("PID", "ITEM", {}, "Missing", "val") is False

    def test_invalid_option(self, capsys):
        field_map = {"Status": {"id": "F1", "options": {"Done": "OPT1"}}}
        assert pm._set_project_field("PID", "ITEM", field_map, "Status", "Invalid") is False
