"""Tests for project_manager.py -- local JSON management, no API calls."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest

# Add parent dir so we can import the module directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import project_manager as pm


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


SAMPLE_SPRINT = {
    "sprint": 1,
    "milestone": "v0.1.0",
    "description": "Sprint 1",
    "due_date": "2026-03-02",
    "tasks": [
        {
            "id": "T-001",
            "type": "task",
            "parent_story_id": "SK-001",
            "labels": ["infra"],
            "title": "Setup CI pipeline",
            "description": "Set up CI",
            "status": "Done",
            "priority": "P0",
            "complexity": "S",
            "milestone": "v0.1.0",
            "issue_number": 1,
            "start_date": "2026-01-01",
            "target_date": "2026-01-15",
        },
        {
            "id": "T-002",
            "type": "task",
            "parent_story_id": "SK-001",
            "labels": ["feature"],
            "title": "Add auth module",
            "description": "Implement auth",
            "status": "In progress",
            "priority": "P1",
            "complexity": "M",
            "milestone": "v0.1.0",
            "issue_number": 2,
            "start_date": "",
            "target_date": "",
        },
        {
            "id": "T-003",
            "type": "task",
            "parent_story_id": "TS-001",
            "labels": ["bug"],
            "title": "Fix login bug",
            "description": "Login broken",
            "status": "Ready",
            "priority": "P0",
            "complexity": "S",
            "milestone": "v0.1.0",
            "issue_number": 3,
            "start_date": "2026-01-02",
            "target_date": "2026-01-05",
        },
    ],
}

SAMPLE_STORIES = {
    "project": "Test",
    "goal": "Test goal",
    "dates": {"start": "2026-01-01", "end": "2026-03-01"},
    "totalPoints": 10,
    "stories": [
        {
            "id": "SK-001",
            "type": "Spike",
            "labels": ["spike", "research"],
            "title": "Research feature X",
            "description": "Research",
            "points": 3,
            "status": "In progress",
            "tdd": False,
            "startDate": "2026-01-01",
            "targetDate": "2026-01-15",
            "priority": "P0",
            "milestone": "v0.1.0",
            "issue_number": 101,
        },
        {
            "id": "TS-001",
            "type": "Tech",
            "labels": ["setup"],
            "title": "Project setup",
            "description": "Setup",
            "points": 5,
            "status": "Ready",
            "tdd": True,
            "startDate": "",
            "targetDate": "",
            "priority": "P1",
            "milestone": "v0.1.0",
            "issue_number": 102,
        },
    ],
}


@pytest.fixture
def sprint_file(tmp_path):
    p = tmp_path / "sprint.json"
    p.write_text(json.dumps(SAMPLE_SPRINT), encoding="utf-8")
    return p


@pytest.fixture
def stories_file(tmp_path):
    p = tmp_path / "stories.json"
    p.write_text(json.dumps(SAMPLE_STORIES), encoding="utf-8")
    return p


@pytest.fixture
def all_items(sprint_file, stories_file):
    return pm._load_all_items(sprint_file, stories_file)


def _make_update_args(**overrides):
    defaults = dict(
        key="T-001", status=None, priority=None, complexity=None,
        title=None, description=None, start_date=None, target_date=None,
        tdd=None, force=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_list_args(**overrides):
    defaults = dict(
        status=None, priority=None, milestone=None, assignee=None,
        label=None, complexity=None, type=None, story=None, sort_by=None,
        reverse=False, wide=False, keys_only=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_view_args(**overrides):
    defaults = dict(key="SK-001", raw=False, template=None)
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _make_summary_args(**overrides):
    defaults = dict(group_by="status")
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


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
        assert pm._sort_key("status", {"status": "Backlog"}) == 4

    def test_status_in_review(self):
        assert pm._sort_key("status", {"status": "In review"}) == 1

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
    def test_find_by_key(self, all_items):
        assert pm._find_task(all_items, "SK-001")["title"] == "Research feature X"

    def test_find_by_key_case_insensitive(self, all_items):
        assert pm._find_task(all_items, "sk-001")["title"] == "Research feature X"

    def test_find_by_issue_number(self, all_items):
        assert pm._find_task(all_items, "102")["id"] == "TS-001"

    def test_not_found(self, all_items):
        assert pm._find_task(all_items, "TS-999") is None


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
# _next_id
# ---------------------------------------------------------------------------


class TestNextId:
    def test_first_id(self):
        assert pm._next_id("T", []) == "T-001"

    def test_increment(self):
        assert pm._next_id("T", ["T-001", "T-002"]) == "T-003"

    def test_gap(self):
        assert pm._next_id("T", ["T-001", "T-005"]) == "T-006"

    def test_mixed_prefixes(self):
        assert pm._next_id("SK", ["SK-001", "TS-002", "SK-003"]) == "SK-004"

    def test_ignores_non_matching(self):
        assert pm._next_id("T", ["SK-001", "TS-002"]) == "T-001"


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


class TestLoadSprint:
    def test_load_existing(self, sprint_file):
        data = pm._load_sprint(sprint_file)
        assert data["sprint"] == 1
        assert len(data["tasks"]) == 3

    def test_load_missing(self, tmp_path):
        data = pm._load_sprint(tmp_path / "missing.json")
        assert data["tasks"] == []
        assert data["sprint"] == 0


class TestLoadStories:
    def test_load_existing(self, stories_file):
        data = pm._load_stories(stories_file)
        assert len(data["stories"]) == 2

    def test_load_missing(self, tmp_path):
        data = pm._load_stories(tmp_path / "missing.json")
        assert data["stories"] == []


class TestSaveSprint:
    def test_save_and_reload(self, tmp_path):
        p = tmp_path / "sprint.json"
        data = {"sprint": 2, "milestone": "v0.2", "description": "", "due_date": "", "tasks": []}
        pm._save_sprint(data, p)
        loaded = json.loads(p.read_text(encoding="utf-8"))
        assert loaded["sprint"] == 2

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "sub" / "dir" / "sprint.json"
        pm._save_sprint({"sprint": 1, "tasks": []}, p)
        assert p.exists()


class TestSaveStories:
    def test_save_and_reload(self, tmp_path):
        p = tmp_path / "stories.json"
        data = {"project": "X", "stories": [{"id": "SK-001"}]}
        pm._save_stories(data, p)
        loaded = json.loads(p.read_text(encoding="utf-8"))
        assert loaded["stories"][0]["id"] == "SK-001"


# ---------------------------------------------------------------------------
# _load_all_items
# ---------------------------------------------------------------------------


class TestLoadAllItems:
    def test_combines_stories_and_tasks(self, sprint_file, stories_file):
        items = pm._load_all_items(sprint_file, stories_file)
        # 2 stories + 3 tasks
        assert len(items) == 5

    def test_stories_come_first(self, sprint_file, stories_file):
        items = pm._load_all_items(sprint_file, stories_file)
        assert items[0]["id"] == "SK-001"
        assert items[1]["id"] == "TS-001"

    def test_tasks_have_parent_id(self, sprint_file, stories_file):
        items = pm._load_all_items(sprint_file, stories_file)
        task_items = [i for i in items if i["id"].startswith("T-")]
        assert all(i["parent_id"] for i in task_items)


# ---------------------------------------------------------------------------
# cmd_list
# ---------------------------------------------------------------------------


class TestCmdList:
    def test_list_all(self, all_items, capsys):
        args = _make_list_args()
        assert pm.cmd_list(all_items, args) == 0
        out = capsys.readouterr().out
        assert "SK-001" in out
        assert "T-001" in out
        assert "5 task(s)" in out

    def test_filter_by_status(self, all_items, capsys):
        args = _make_list_args(status="Done")
        pm.cmd_list(all_items, args)
        out = capsys.readouterr().out
        assert "T-001" in out
        assert "1 task(s)" in out

    def test_filter_by_priority(self, all_items, capsys):
        args = _make_list_args(priority="P0")
        pm.cmd_list(all_items, args)
        out = capsys.readouterr().out
        assert "SK-001" in out
        assert "T-001" in out
        assert "T-003" in out

    def test_sort_by_priority(self, all_items, capsys):
        args = _make_list_args(sort_by="priority")
        pm.cmd_list(all_items, args)
        out = capsys.readouterr().out
        lines = [l for l in out.strip().split("\n") if "P0" in l or "P1" in l]
        assert len(lines) > 0

    def test_keys_only(self, all_items, capsys):
        args = _make_list_args(keys_only=True)
        pm.cmd_list(all_items, args)
        out = capsys.readouterr().out.strip()
        assert "SK-001" in out
        assert "T-001" in out

    def test_wide_columns(self, all_items, capsys):
        args = _make_list_args(wide=True)
        pm.cmd_list(all_items, args)
        out = capsys.readouterr().out
        assert "START" in out
        assert "TARGET" in out

    def test_filter_by_label(self, all_items, capsys):
        args = _make_list_args(label="bug")
        pm.cmd_list(all_items, args)
        out = capsys.readouterr().out
        assert "T-003" in out
        assert "1 task(s)" in out

    def test_filter_by_complexity(self, all_items, capsys):
        args = _make_list_args(complexity="S")
        pm.cmd_list(all_items, args)
        out = capsys.readouterr().out
        assert "T-001" in out
        assert "T-003" in out

    def test_filter_by_story(self, all_items, capsys):
        args = _make_list_args(story="SK-001")
        pm.cmd_list(all_items, args)
        out = capsys.readouterr().out
        assert "T-001" in out
        assert "T-002" in out
        assert "T-003" not in out
        assert "2 task(s)" in out


# ---------------------------------------------------------------------------
# cmd_view
# ---------------------------------------------------------------------------


class TestCmdView:
    def test_view_raw(self, all_items, capsys):
        args = _make_view_args(key="SK-001", raw=True)
        assert pm.cmd_view(all_items, args) == 0
        out = capsys.readouterr().out
        assert "Research feature X" in out
        assert "In progress" in out

    def test_view_not_found(self, all_items, capsys):
        args = _make_view_args(key="TS-999")
        assert pm.cmd_view(all_items, args) == 1

    def test_view_story_shows_children(self, all_items, capsys):
        args = _make_view_args(key="SK-001", raw=True)
        pm.cmd_view(all_items, args)
        out = capsys.readouterr().out
        assert "Child tasks" in out
        assert "T-001" in out
        assert "T-002" in out


# ---------------------------------------------------------------------------
# cmd_summary
# ---------------------------------------------------------------------------


class TestCmdSummary:
    def test_summary_by_status(self, all_items, capsys):
        args = _make_summary_args(group_by="status")
        assert pm.cmd_summary(all_items, args) == 0
        out = capsys.readouterr().out
        assert "Summary by status" in out
        assert "Done" in out
        assert "In progress" in out

    def test_summary_by_priority(self, all_items, capsys):
        args = _make_summary_args(group_by="priority")
        assert pm.cmd_summary(all_items, args) == 0
        out = capsys.readouterr().out
        assert "Summary by priority" in out
        assert "P0" in out
        assert "P1" in out


# ---------------------------------------------------------------------------
# cmd_create_sprint
# ---------------------------------------------------------------------------


class TestCreateSprint:
    def test_creates_sprint(self, tmp_path, capsys):
        sprint_path = tmp_path / "sprint.json"
        args = argparse.Namespace(
            number=2, milestone="v0.2.0", description="Sprint 2", due_date="2026-04-01",
            _sprint_path=sprint_path,
        )
        assert pm.cmd_create_sprint(args) == 0
        data = json.loads(sprint_path.read_text(encoding="utf-8"))
        assert data["sprint"] == 2
        assert data["milestone"] == "v0.2.0"
        assert data["tasks"] == []
        assert "Created sprint 2" in capsys.readouterr().out

    def test_creates_sprint_minimal(self, tmp_path):
        sprint_path = tmp_path / "sprint.json"
        args = argparse.Namespace(
            number=1, milestone=None, description=None, due_date=None,
            _sprint_path=sprint_path,
        )
        pm.cmd_create_sprint(args)
        data = json.loads(sprint_path.read_text(encoding="utf-8"))
        assert data["milestone"] == ""


# ---------------------------------------------------------------------------
# cmd_add_story
# ---------------------------------------------------------------------------


class TestAddStory:
    def test_adds_spike(self, stories_file, capsys):
        args = argparse.Namespace(
            type="Spike", title="New spike", description="desc",
            points=2, priority="P1", milestone="v0.2.0", tdd=False,
            _stories_path=stories_file,
        )
        assert pm.cmd_add_story(args) == 0
        data = json.loads(stories_file.read_text(encoding="utf-8"))
        assert len(data["stories"]) == 3
        new = data["stories"][-1]
        assert new["id"] == "SK-002"
        assert new["type"] == "Spike"
        assert new["title"] == "New spike"
        assert "Added story SK-002" in capsys.readouterr().out

    def test_adds_tech_story(self, stories_file):
        args = argparse.Namespace(
            type="Tech", title="Tech story", description=None,
            points=None, priority=None, milestone=None, tdd=False,
            _stories_path=stories_file,
        )
        pm.cmd_add_story(args)
        data = json.loads(stories_file.read_text(encoding="utf-8"))
        new = data["stories"][-1]
        assert new["id"] == "TS-002"
        assert new["type"] == "Tech"

    def test_tdd_defaults_false(self, stories_file):
        args = argparse.Namespace(
            type="Tech", title="No TDD story", description=None,
            points=None, priority=None, milestone=None, tdd=False,
            _stories_path=stories_file,
        )
        pm.cmd_add_story(args)
        data = json.loads(stories_file.read_text(encoding="utf-8"))
        assert data["stories"][-1]["tdd"] is False

    def test_tdd_true(self, stories_file):
        args = argparse.Namespace(
            type="Tech", title="TDD story", description=None,
            points=None, priority=None, milestone=None, tdd=True,
            _stories_path=stories_file,
        )
        pm.cmd_add_story(args)
        data = json.loads(stories_file.read_text(encoding="utf-8"))
        assert data["stories"][-1]["tdd"] is True

    def test_adds_story_type(self, stories_file):
        args = argparse.Namespace(
            type="Story", title="User story", description=None,
            points=None, priority=None, milestone=None, tdd=False,
            _stories_path=stories_file,
        )
        pm.cmd_add_story(args)
        data = json.loads(stories_file.read_text(encoding="utf-8"))
        new = data["stories"][-1]
        # Story type uses TS prefix
        assert new["id"] == "TS-002"

    def test_adds_user_story(self, stories_file, capsys):
        args = argparse.Namespace(
            type="User Story", title="As a user I want X", description="desc",
            points=3, priority="P1", milestone=None, tdd=False,
            _stories_path=stories_file,
        )
        assert pm.cmd_add_story(args) == 0
        data = json.loads(stories_file.read_text(encoding="utf-8"))
        new = data["stories"][-1]
        assert new["id"] == "US-001"
        assert new["type"] == "User Story"
        assert "Added story US-001" in capsys.readouterr().out

    def test_adds_bug(self, stories_file, capsys):
        args = argparse.Namespace(
            type="Bug", title="Fix crash on login", description="desc",
            points=1, priority="P0", milestone=None, tdd=False,
            _stories_path=stories_file,
        )
        assert pm.cmd_add_story(args) == 0
        data = json.loads(stories_file.read_text(encoding="utf-8"))
        new = data["stories"][-1]
        assert new["id"] == "BG-001"
        assert new["type"] == "Bug"
        assert "Added story BG-001" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# cmd_add_task
# ---------------------------------------------------------------------------


class TestAddTask:
    def test_adds_task(self, sprint_file, capsys):
        args = argparse.Namespace(
            parent_story_id="SK-001", title="New task", description="desc",
            priority="P1", complexity="M", labels=["test"],
            _sprint_path=sprint_file,
        )
        assert pm.cmd_add_task(args) == 0
        data = json.loads(sprint_file.read_text(encoding="utf-8"))
        assert len(data["tasks"]) == 4
        new = data["tasks"][-1]
        assert new["id"] == "T-004"
        assert new["parent_story_id"] == "SK-001"
        assert "Added task T-004" in capsys.readouterr().out

    def test_adds_task_minimal(self, sprint_file):
        args = argparse.Namespace(
            parent_story_id="TS-001", title="Minimal task", description=None,
            priority=None, complexity=None, labels=None,
            _sprint_path=sprint_file,
        )
        pm.cmd_add_task(args)
        data = json.loads(sprint_file.read_text(encoding="utf-8"))
        new = data["tasks"][-1]
        assert new["status"] == "Backlog"
        assert new["priority"] == "P2"


# ---------------------------------------------------------------------------
# cmd_update
# ---------------------------------------------------------------------------


class TestUpdateTask:
    def test_update_task_status(self, sprint_file, capsys):
        # T-001 is Done; use force to set to In progress
        args = argparse.Namespace(
            key="T-001", status="In progress", priority=None, complexity=None,
            title=None, description=None, start_date=None, target_date=None, tdd=None,
            force=True, _sprint_path=sprint_file, _stories_path=Path("/nonexistent"),
        )
        assert pm.cmd_update(args) == 0
        data = json.loads(sprint_file.read_text(encoding="utf-8"))
        assert data["tasks"][0]["status"] == "In progress"
        assert "Updated T-001" in capsys.readouterr().out

    def test_update_task_multiple_fields(self, sprint_file):
        # T-002 is In progress -> Done requires In review first; use force
        args = argparse.Namespace(
            key="T-002", status="Done", priority="P0", complexity="L",
            title=None, description=None, start_date=None, target_date=None, tdd=None,
            force=True, _sprint_path=sprint_file, _stories_path=Path("/nonexistent"),
        )
        pm.cmd_update(args)
        data = json.loads(sprint_file.read_text(encoding="utf-8"))
        t = data["tasks"][1]
        assert t["status"] == "Done"
        assert t["priority"] == "P0"
        assert t["complexity"] == "L"

    def test_update_task_not_found(self, sprint_file, capsys):
        args = argparse.Namespace(
            key="T-999", status="Done", priority=None, complexity=None,
            title=None, description=None, start_date=None, target_date=None, tdd=None,
            force=False, _sprint_path=sprint_file, _stories_path=Path("/nonexistent"),
        )
        assert pm.cmd_update(args) == 1
        assert "not found" in capsys.readouterr().err

    def test_nothing_to_update(self, sprint_file, capsys):
        args = argparse.Namespace(
            key="T-001", status=None, priority=None, complexity=None,
            title=None, description=None, start_date=None, target_date=None, tdd=None,
            force=False, _sprint_path=sprint_file, _stories_path=Path("/nonexistent"),
        )
        assert pm.cmd_update(args) == 1
        assert "Nothing to update" in capsys.readouterr().err


class TestUpdateStory:
    def test_update_story_status(self, stories_file, capsys, tmp_path):
        # SK-001 is In progress -> Done requires In review first; use force
        args = argparse.Namespace(
            key="SK-001", status="Done", priority=None, complexity=None,
            title=None, description=None, start_date=None, target_date=None, tdd=None,
            force=True, _sprint_path=tmp_path / "empty.json", _stories_path=stories_file,
        )
        assert pm.cmd_update(args) == 0
        data = json.loads(stories_file.read_text(encoding="utf-8"))
        assert data["stories"][0]["status"] == "Done"

    def test_update_story_dates(self, stories_file, tmp_path):
        args = argparse.Namespace(
            key="TS-001", status=None, priority=None, complexity=None,
            title=None, description=None,
            start_date="2026-03-01", target_date="2026-03-15", tdd=None,
            force=False, _sprint_path=tmp_path / "empty.json", _stories_path=stories_file,
        )
        pm.cmd_update(args)
        data = json.loads(stories_file.read_text(encoding="utf-8"))
        story = data["stories"][1]
        assert story["startDate"] == "2026-03-01"
        assert story["targetDate"] == "2026-03-15"

    def test_update_story_not_found(self, stories_file, capsys, tmp_path):
        args = argparse.Namespace(
            key="SK-999", status="Done", priority=None, complexity=None,
            title=None, description=None, start_date=None, target_date=None, tdd=None,
            force=False, _sprint_path=tmp_path / "empty.json", _stories_path=stories_file,
        )
        assert pm.cmd_update(args) == 1
        assert "not found" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# cmd_progress
# ---------------------------------------------------------------------------


class TestProgress:
    def test_progress_output(self, sprint_file, stories_file, capsys):
        args = argparse.Namespace(
            _sprint_path=sprint_file, _stories_path=stories_file,
        )
        assert pm.cmd_progress(args) == 0
        out = capsys.readouterr().out
        assert "Sprint 1" in out
        assert "1/3 tasks done" in out
        assert "33%" in out

    def test_progress_story_completion(self, sprint_file, stories_file, capsys):
        args = argparse.Namespace(
            _sprint_path=sprint_file, _stories_path=stories_file,
        )
        pm.cmd_progress(args)
        out = capsys.readouterr().out
        assert "Story completion:" in out
        assert "0/2 stories done" in out

    def test_progress_per_story(self, sprint_file, stories_file, capsys):
        args = argparse.Namespace(
            _sprint_path=sprint_file, _stories_path=stories_file,
        )
        pm.cmd_progress(args)
        out = capsys.readouterr().out
        assert "Per-story task completion:" in out
        assert "SK-001" in out
        assert "TS-001" in out

    def test_progress_empty(self, tmp_path, capsys):
        sprint_path = tmp_path / "sprint.json"
        stories_path = tmp_path / "stories.json"
        args = argparse.Namespace(
            _sprint_path=sprint_path, _stories_path=stories_path,
        )
        pm.cmd_progress(args)
        out = capsys.readouterr().out
        assert "No tasks" in out


# ---------------------------------------------------------------------------
# _validate_transition
# ---------------------------------------------------------------------------


class TestValidateTransition:
    def test_valid_transition(self):
        assert pm._validate_transition("Backlog", "Ready") is None

    def test_invalid_transition_returns_message(self):
        err = pm._validate_transition("Backlog", "In progress")
        assert err is not None
        assert "Cannot move" in err
        assert "--force" in err

    def test_unknown_current_status(self):
        err = pm._validate_transition("Limbo", "Ready")
        assert err is not None

    def test_done_to_in_progress(self):
        assert pm._validate_transition("Done", "In progress") is None

    def test_invalid_backlog_to_done(self):
        assert pm._validate_transition("Backlog", "Done") is not None


class TestUpdateGuardrail:
    def test_invalid_transition_blocked(self, sprint_file, capsys):
        # T-003 is Ready; jumping to Done directly should be blocked
        args = argparse.Namespace(
            key="T-003", status="Done", priority=None, complexity=None,
            title=None, description=None, start_date=None, target_date=None, tdd=None,
            force=False, _sprint_path=sprint_file, _stories_path=Path("/nonexistent"),
        )
        assert pm.cmd_update(args) == 1
        assert "Cannot move" in capsys.readouterr().err

    def test_invalid_transition_bypassed_with_force(self, sprint_file, capsys):
        # T-003 is Ready; --force allows jumping to Done
        args = argparse.Namespace(
            key="T-003", status="Done", priority=None, complexity=None,
            title=None, description=None, start_date=None, target_date=None, tdd=None,
            force=True, _sprint_path=sprint_file, _stories_path=Path("/nonexistent"),
        )
        assert pm.cmd_update(args) == 0
        data = json.loads(sprint_file.read_text(encoding="utf-8"))
        t003 = next(t for t in data["tasks"] if t["id"] == "T-003")
        assert t003["status"] == "Done"

    def test_valid_transition_passes(self, sprint_file, capsys):
        # T-003 is Ready -> In progress is valid
        args = argparse.Namespace(
            key="T-003", status="In progress", priority=None, complexity=None,
            title=None, description=None, start_date=None, target_date=None, tdd=None,
            force=False, _sprint_path=sprint_file, _stories_path=Path("/nonexistent"),
        )
        assert pm.cmd_update(args) == 0
        assert "Updated T-003" in capsys.readouterr().out

    def test_non_status_update_no_guardrail(self, sprint_file, capsys):
        # Updating priority only should never trigger the guardrail
        args = argparse.Namespace(
            key="T-003", status=None, priority="P0", complexity=None,
            title=None, description=None, start_date=None, target_date=None, tdd=None,
            force=False, _sprint_path=sprint_file, _stories_path=Path("/nonexistent"),
        )
        assert pm.cmd_update(args) == 0


# ---------------------------------------------------------------------------
# _is_unblocked
# ---------------------------------------------------------------------------


class TestIsUnblocked:
    def test_is_unblocked_empty_list(self):
        assert pm._is_unblocked([], {}) is True

    def test_is_unblocked_all_done(self):
        assert pm._is_unblocked(["SK-001", "SK-002"], {"SK-001": "Done", "SK-002": "Done"}) is True

    def test_is_unblocked_not_done(self):
        assert pm._is_unblocked(["SK-001"], {"SK-001": "Backlog"}) is False

    def test_is_unblocked_missing_id(self):
        # Unknown dep ID treated as not Done
        assert pm._is_unblocked(["SK-999"], {}) is False


# ---------------------------------------------------------------------------
# cmd_unblocked fixtures
# ---------------------------------------------------------------------------

SAMPLE_SPRINT_UNBLOCKED = {
    "sprint": 1,
    "milestone": "v0.1.0",
    "tasks": [
        {
            "id": "T-001", "title": "Task A", "status": "Backlog",
            "blocked_by": [], "is_blocking": [], "type": "task",
            "parent_story_id": "SK-001",
        },
        {
            "id": "T-002", "title": "Task B", "status": "Backlog",
            "blocked_by": ["SK-001"], "is_blocking": [], "type": "task",
            "parent_story_id": "SK-001",
        },
        {
            "id": "T-003", "title": "Task C", "status": "Done",
            "blocked_by": [], "is_blocking": [], "type": "task",
            "parent_story_id": "SK-001",
        },
    ],
}

SAMPLE_STORIES_UNBLOCKED = {
    "stories": [
        {
            "id": "SK-001", "title": "Story A", "status": "Done",
            "blocked_by": [], "is_blocking": [],
        },
        {
            "id": "SK-002", "title": "Story B", "status": "Backlog",
            "blocked_by": ["SK-001"], "is_blocking": [],
        },
        {
            "id": "SK-003", "title": "Story C", "status": "Backlog",
            "blocked_by": ["SK-002"], "is_blocking": [],
        },
    ],
}


@pytest.fixture
def unblocked_sprint_file(tmp_path):
    p = tmp_path / "sprint.json"
    p.write_text(json.dumps(SAMPLE_SPRINT_UNBLOCKED), encoding="utf-8")
    return p


@pytest.fixture
def unblocked_stories_file(tmp_path):
    p = tmp_path / "stories.json"
    p.write_text(json.dumps(SAMPLE_STORIES_UNBLOCKED), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# cmd_unblocked
# ---------------------------------------------------------------------------


class TestUnblocked:
    def test_unblocked_lists_correct_items(self, unblocked_sprint_file, unblocked_stories_file, capsys):
        args = argparse.Namespace(
            _sprint_path=unblocked_sprint_file, _stories_path=unblocked_stories_file,
            promote=False, json=False,
        )
        assert pm.cmd_unblocked(args) == 0
        out = capsys.readouterr().out
        # T-001 unblocked (no deps), SK-002 unblocked (SK-001 is Done)
        assert "T-001" in out
        assert "SK-002" in out
        # T-002 blocked by SK-001 which is Done -> should appear
        assert "T-002" in out
        # T-003 is Done -> skipped
        assert "T-003" not in out
        # SK-001 is Done -> skipped
        assert "SK-001" not in out
        # SK-003 blocked by SK-002 which is Backlog -> not unblocked
        assert "SK-003" not in out

    def test_unblocked_skips_done_items(self, unblocked_sprint_file, unblocked_stories_file, capsys):
        args = argparse.Namespace(
            _sprint_path=unblocked_sprint_file, _stories_path=unblocked_stories_file,
            promote=False, json=False,
        )
        pm.cmd_unblocked(args)
        out = capsys.readouterr().out
        assert "T-003" not in out
        assert "SK-001" not in out

    def test_unblocked_promote(self, unblocked_sprint_file, unblocked_stories_file, capsys):
        args = argparse.Namespace(
            _sprint_path=unblocked_sprint_file, _stories_path=unblocked_stories_file,
            promote=True, json=False,
        )
        assert pm.cmd_unblocked(args) == 0
        out = capsys.readouterr().out
        assert "Promoted" in out

        sprint_data = json.loads(unblocked_sprint_file.read_text(encoding="utf-8"))
        stories_data = json.loads(unblocked_stories_file.read_text(encoding="utf-8"))

        # T-001 was Backlog and unblocked -> now Ready
        t001 = next(t for t in sprint_data["tasks"] if t["id"] == "T-001")
        assert t001["status"] == "Ready"

        # SK-002 was Backlog and unblocked (SK-001 Done) -> now Ready
        sk002 = next(s for s in stories_data["stories"] if s["id"] == "SK-002")
        assert sk002["status"] == "Ready"

        # T-003 was Done -> stays Done
        t003 = next(t for t in sprint_data["tasks"] if t["id"] == "T-003")
        assert t003["status"] == "Done"

    def test_unblocked_promote_skips_already_ready(self, tmp_path, capsys):
        sprint_data = {
            "sprint": 1, "milestone": "v0.1.0",
            "tasks": [
                {"id": "T-001", "title": "Task A", "status": "Ready", "blocked_by": [], "type": "task"},
            ],
        }
        stories_data = {"stories": []}
        sprint_file = tmp_path / "sprint.json"
        stories_file = tmp_path / "stories.json"
        sprint_file.write_text(json.dumps(sprint_data), encoding="utf-8")
        stories_file.write_text(json.dumps(stories_data), encoding="utf-8")

        args = argparse.Namespace(
            _sprint_path=sprint_file, _stories_path=stories_file,
            promote=True, json=False,
        )
        pm.cmd_unblocked(args)
        out = capsys.readouterr().out
        # Promoted 0 because T-001 is already Ready (not Backlog)
        assert "Promoted 0" in out

        saved = json.loads(sprint_file.read_text(encoding="utf-8"))
        assert saved["tasks"][0]["status"] == "Ready"

    def test_unblocked_filter_by_story(self, unblocked_sprint_file, unblocked_stories_file, capsys):
        args = argparse.Namespace(
            _sprint_path=unblocked_sprint_file, _stories_path=unblocked_stories_file,
            promote=False, story="SK-001", json=False,
        )
        pm.cmd_unblocked(args)
        out = capsys.readouterr().out
        # Only tasks whose parent_story_id == SK-001 and story itself if it matches
        assert "T-001" in out   # parent_story_id=SK-001, unblocked
        assert "T-002" in out   # parent_story_id=SK-001, unblocked (SK-001 is Done)
        assert "SK-002" not in out  # story filter only matches story id SK-001, not SK-002

# ---------------------------------------------------------------------------
# cmd_complete_sprint
# ---------------------------------------------------------------------------


class TestCompleteSprint:
    def test_archives_sprint_files(self, tmp_path, capsys):
        sprint_path = tmp_path / "sprint.json"
        stories_path = tmp_path / "stories.json"
        sprint_data = {"sprint": 1, "milestone": "v0.1.0", "tasks": []}
        stories_data = {"project": "X", "stories": []}
        sprint_path.write_text(json.dumps(sprint_data), encoding="utf-8")
        stories_path.write_text(json.dumps(stories_data), encoding="utf-8")

        args = argparse.Namespace(
            _sprint_path=sprint_path, _stories_path=stories_path,
        )
        assert pm.cmd_complete_sprint(args) == 0

        archive_dir = tmp_path / "archive"
        assert archive_dir.exists()
        assert (archive_dir / "sprint-1.json").exists()
        assert (archive_dir / "stories-1.json").exists()
        assert not sprint_path.exists()
        assert not stories_path.exists()
        assert "Archived sprint 1" in capsys.readouterr().out

    def test_archive_creates_directory(self, tmp_path):
        sprint_path = tmp_path / "sprint.json"
        stories_path = tmp_path / "stories.json"
        sprint_data = {"sprint": 2, "milestone": "v0.2.0", "tasks": []}
        stories_data = {"project": "X", "stories": []}
        sprint_path.write_text(json.dumps(sprint_data), encoding="utf-8")
        stories_path.write_text(json.dumps(stories_data), encoding="utf-8")

        args = argparse.Namespace(
            _sprint_path=sprint_path, _stories_path=stories_path,
        )
        pm.cmd_complete_sprint(args)

        archive_dir = tmp_path / "archive"
        assert (archive_dir / "sprint-2.json").exists()
        assert (archive_dir / "stories-2.json").exists()

    def test_missing_sprint_file(self, tmp_path, capsys):
        sprint_path = tmp_path / "sprint.json"
        stories_path = tmp_path / "stories.json"
        args = argparse.Namespace(
            _sprint_path=sprint_path, _stories_path=stories_path,
        )
        assert pm.cmd_complete_sprint(args) == 1
        assert "No active sprint" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# cmd_unblocked (continued)
# ---------------------------------------------------------------------------


    def test_unblocked_no_items(self, tmp_path, capsys):
        # All items are Done -> no unblocked
        sprint_data = {
            "sprint": 1, "milestone": "v0.1.0",
            "tasks": [
                {"id": "T-001", "title": "Task A", "status": "Done", "blocked_by": []},
            ],
        }
        stories_data = {"stories": []}
        sprint_file = tmp_path / "sprint.json"
        stories_file = tmp_path / "stories.json"
        sprint_file.write_text(json.dumps(sprint_data), encoding="utf-8")
        stories_file.write_text(json.dumps(stories_data), encoding="utf-8")

        args = argparse.Namespace(
            _sprint_path=sprint_file, _stories_path=stories_file,
            promote=False, json=False,
        )
        assert pm.cmd_unblocked(args) == 0
        out = capsys.readouterr().out
        assert "No unblocked items found." in out

    def test_unblocked_json_output(self, unblocked_sprint_file, unblocked_stories_file, capsys):
        args = argparse.Namespace(
            _sprint_path=unblocked_sprint_file, _stories_path=unblocked_stories_file,
            promote=False, json=True,
        )
        assert pm.cmd_unblocked(args) == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, list)
        ids = [item["id"] for item in data]
        assert "T-001" in ids
        assert "SK-002" in ids
        assert "T-002" in ids
        # Done items excluded
        assert "T-003" not in ids
        assert "SK-001" not in ids
        # Each item has required fields
        for item in data:
            assert "id" in item
            assert "type" in item
            assert "status" in item
            assert "title" in item
            assert "description" in item
            assert "blocked_by" in item
        # Tasks have parent_story_id
        tasks = [i for i in data if i["type"] == "task"]
        for t in tasks:
            assert "parent_story_id" in t
