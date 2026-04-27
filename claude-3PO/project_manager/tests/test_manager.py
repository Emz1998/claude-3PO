"""Tests for project_manager.manager — single-backlog schema."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from project_manager import ProjectManager
from project_manager import manager as pm


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


SAMPLE_BACKLOG: dict = {
    "project": "Test",
    "goal": "Test goal",
    "dates": {"start": "2026-01-01", "end": "2026-03-01"},
    "totalPoints": 10,
    "stories": [
        {
            "id": "SK-001",
            "type": "Spike",
            "milestone": "v0.1.0",
            "labels": ["spike", "research"],
            "title": "Research feature X",
            "description": "Research",
            "points": 3,
            "status": "In progress",
            "tdd": False,
            "priority": "P0",
            "is_blocking": [],
            "blocked_by": [],
            "acceptance_criteria": ["AC1", "AC2"],
            "start_date": "2026-01-01",
            "target_date": "2026-01-15",
            "issue_number": 101,
            "tasks": [
                {
                    "id": "T-001",
                    "type": "task",
                    "labels": ["infra"],
                    "title": "Setup CI pipeline",
                    "description": "Set up CI",
                    "status": "Done",
                    "priority": "P0",
                    "complexity": "S",
                    "acceptance_criteria": [],
                    "item_type": "task",
                    "start_date": "2026-01-01",
                    "target_date": "2026-01-15",
                },
                {
                    "id": "T-002",
                    "type": "task",
                    "labels": ["feature"],
                    "title": "Add auth module",
                    "description": "Implement auth",
                    "status": "In progress",
                    "priority": "P1",
                    "complexity": "M",
                    "acceptance_criteria": [],
                    "item_type": "task",
                    "start_date": "",
                    "target_date": "",
                },
            ],
        },
        {
            "id": "TS-001",
            "type": "Tech",
            "milestone": "v0.1.0",
            "labels": ["setup"],
            "title": "Project setup",
            "description": "Setup",
            "points": 5,
            "status": "Ready",
            "tdd": True,
            "priority": "P1",
            "is_blocking": [],
            "blocked_by": [],
            "acceptance_criteria": [],
            "start_date": "",
            "target_date": "",
            "issue_number": 102,
            "tasks": [
                {
                    "id": "T-003",
                    "type": "task",
                    "labels": ["bug"],
                    "title": "Fix login bug",
                    "description": "Login broken",
                    "status": "Ready",
                    "priority": "P0",
                    "complexity": "S",
                    "acceptance_criteria": [],
                    "item_type": "task",
                    "start_date": "2026-01-02",
                    "target_date": "2026-01-05",
                },
            ],
        },
    ],
}


@pytest.fixture
def backlog_file(tmp_path):
    p = tmp_path / "backlog.json"
    p.write_text(json.dumps(SAMPLE_BACKLOG), encoding="utf-8")
    return p


@pytest.fixture
def pm_instance(backlog_file):
    return ProjectManager(backlog_file)


@pytest.fixture
def all_items(pm_instance):
    return pm_instance.load_all_items()


# ---------------------------------------------------------------------------
# Pure helper tests
# ---------------------------------------------------------------------------


class TestSortKey:
    def test_priority_order(self):
        assert pm._sort_key("priority", {"priority": "P0"}) == 0
        assert pm._sort_key("priority", {"priority": "Unknown"}) == 99

    def test_status_order(self):
        assert pm._sort_key("status", {"status": "Done"}) == 0
        assert pm._sort_key("status", {"status": "Backlog"}) == 4

    def test_complexity_order(self):
        assert pm._sort_key("complexity", {"complexity": "XS"}) == 0
        assert pm._sort_key("complexity", {"complexity": "XL"}) == 4

    def test_numeric_field(self):
        assert pm._sort_key("points", {"points": 5}) == 5
        assert pm._sort_key("points", {"points": None}) == 0

    def test_string_field(self):
        assert pm._sort_key("title", {"title": "Hello"}) == "hello"


class TestMatches:
    def test_exact_match(self):
        task = {"status": "Done", "priority": "P0"}
        assert pm._matches(task, {"status": "Done"}) is True
        assert pm._matches(task, {"status": "Ready"}) is False

    def test_case_insensitive(self):
        assert pm._matches({"status": "In progress"}, {"status": "in progress"}) is True

    def test_list_field(self):
        assert pm._matches({"labels": ["bug"]}, {"labels": "bug"}) is True
        assert pm._matches({"labels": ["bug"]}, {"labels": "docs"}) is False

    def test_missing_field(self):
        assert pm._matches({}, {"status": "Done"}) is False

    def test_empty_filters(self):
        assert pm._matches({"status": "Done"}, {}) is True


class TestTruncate:
    def test_short(self):
        assert pm._truncate("hello", 10) == "hello"

    def test_long(self):
        assert pm._truncate("hello world", 6) == "hello\u2026"


class TestFormatList:
    def test_list(self):
        assert pm._format_list(["a", "b"]) == "a, b"

    def test_empty_list(self):
        assert pm._format_list([]) == "(none)"

    def test_none(self):
        assert pm._format_list(None) == "(none)"

    def test_value(self):
        assert pm._format_list("hello") == "hello"


class TestNextId:
    def test_first(self):
        assert pm._next_id("T", []) == "T-001"

    def test_increment(self):
        assert pm._next_id("T", ["T-001", "T-002"]) == "T-003"

    def test_gap(self):
        assert pm._next_id("T", ["T-001", "T-005"]) == "T-006"

    def test_mixed_prefixes(self):
        assert pm._next_id("SK", ["SK-001", "TS-002", "SK-003"]) == "SK-004"


class TestFindTask:
    def test_by_key(self, all_items):
        assert pm._find_task(all_items, "SK-001")["title"] == "Research feature X"

    def test_case_insensitive(self, all_items):
        assert pm._find_task(all_items, "sk-001")["title"] == "Research feature X"

    def test_by_issue_number(self, all_items):
        assert pm._find_task(all_items, "102")["id"] == "TS-001"

    def test_not_found(self, all_items):
        assert pm._find_task(all_items, "TS-999") is None


class TestValidateTransition:
    def test_valid(self):
        assert pm._validate_transition("Backlog", "Ready") is None

    def test_invalid_returns_message(self):
        err = pm._validate_transition("Backlog", "In progress")
        assert err is not None
        assert "Cannot move" in err

    def test_unknown_current(self):
        assert pm._validate_transition("Limbo", "Ready") is not None

    def test_done_to_in_progress(self):
        assert pm._validate_transition("Done", "In progress") is None


class TestIsUnblocked:
    def test_empty(self):
        assert pm._is_unblocked([], {}) is True

    def test_all_done(self):
        assert pm._is_unblocked(["A"], {"A": "Done"}) is True

    def test_not_done(self):
        assert pm._is_unblocked(["A"], {"A": "Backlog"}) is False

    def test_missing_id(self):
        assert pm._is_unblocked(["X"], {}) is False


# ---------------------------------------------------------------------------
# I/O methods
# ---------------------------------------------------------------------------


class TestLoadBacklog:
    def test_existing(self, backlog_file):
        data = ProjectManager(backlog_file).load_backlog()
        assert data["project"] == "Test"
        assert len(data["stories"]) == 2

    def test_missing(self, tmp_path):
        data = ProjectManager(tmp_path / "missing.json").load_backlog()
        assert data["stories"] == []
        assert data["totalPoints"] == 0


class TestSaveBacklog:
    def test_save_and_reload(self, tmp_path):
        p = tmp_path / "backlog.json"
        ProjectManager(p).save_backlog({"project": "X", "stories": []})
        loaded = json.loads(p.read_text(encoding="utf-8"))
        assert loaded["project"] == "X"

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "sub" / "dir" / "backlog.json"
        ProjectManager(p).save_backlog({"stories": []})
        assert p.exists()


class TestLoadAllItems:
    def test_counts(self, pm_instance):
        assert len(pm_instance.load_all_items()) == 5

    def test_stories_first(self, pm_instance):
        items = pm_instance.load_all_items()
        assert items[0]["id"] == "SK-001"
        assert items[1]["id"] == "TS-001"

    def test_tasks_get_parent_id(self, pm_instance):
        items = pm_instance.load_all_items()
        t001 = next(i for i in items if i["id"] == "T-001")
        t003 = next(i for i in items if i["id"] == "T-003")
        assert t001["parent_id"] == "SK-001"
        assert t003["parent_id"] == "TS-001"

    def test_task_inherits_milestone(self, pm_instance):
        items = pm_instance.load_all_items()
        t001 = next(i for i in items if i["id"] == "T-001")
        assert t001["milestone"] == "v0.1.0"


# ---------------------------------------------------------------------------
# list_items
# ---------------------------------------------------------------------------


class TestCmdList:
    def test_list_all(self, pm_instance, capsys):
        assert pm_instance.list_items() == 0
        out = capsys.readouterr().out
        assert "SK-001" in out
        assert "T-001" in out
        assert "5 task(s)" in out

    def test_filter_by_status(self, pm_instance, capsys):
        pm_instance.list_items(status="Done")
        out = capsys.readouterr().out
        assert "T-001" in out
        assert "1 task(s)" in out

    def test_filter_by_priority(self, pm_instance, capsys):
        pm_instance.list_items(priority="P0")
        out = capsys.readouterr().out
        assert "SK-001" in out
        assert "T-003" in out

    def test_sort_by_priority(self, pm_instance, capsys):
        pm_instance.list_items(sort_by="priority")
        out = capsys.readouterr().out
        lines = [l for l in out.split("\n") if "P0" in l or "P1" in l]
        assert len(lines) > 0

    def test_keys_only(self, pm_instance, capsys):
        pm_instance.list_items(keys_only=True)
        out = capsys.readouterr().out.strip()
        assert "SK-001" in out and "T-001" in out

    def test_wide(self, pm_instance, capsys):
        pm_instance.list_items(wide=True)
        out = capsys.readouterr().out
        assert "START" in out and "TARGET" in out

    def test_filter_by_label(self, pm_instance, capsys):
        pm_instance.list_items(label="bug")
        out = capsys.readouterr().out
        assert "T-003" in out
        assert "1 task(s)" in out

    def test_filter_by_complexity(self, pm_instance, capsys):
        pm_instance.list_items(complexity="S")
        out = capsys.readouterr().out
        assert "T-001" in out and "T-003" in out

    def test_filter_by_story(self, pm_instance, capsys):
        pm_instance.list_items(story="SK-001")
        out = capsys.readouterr().out
        assert "T-001" in out
        assert "T-002" in out
        assert "T-003" not in out


# ---------------------------------------------------------------------------
# view
# ---------------------------------------------------------------------------


class TestCmdView:
    def test_view_raw(self, pm_instance, capsys):
        assert pm_instance.view(key="SK-001", raw=True) == 0
        out = capsys.readouterr().out
        assert "Research feature X" in out
        assert "In progress" in out

    def test_view_not_found(self, pm_instance):
        assert pm_instance.view(key="TS-999") == 1

    def test_view_story_shows_children(self, pm_instance, capsys):
        pm_instance.view(key="SK-001", raw=True)
        out = capsys.readouterr().out
        assert "Child tasks" in out
        assert "T-001" in out
        assert "T-002" in out

    def test_view_ac_only(self, pm_instance, capsys):
        assert pm_instance.view(key="SK-001", ac=True) == 0
        out = capsys.readouterr().out
        assert "AC1" in out and "AC2" in out


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------


class TestCmdSummary:
    def test_by_status(self, pm_instance, capsys):
        assert pm_instance.summary(group_by="status") == 0
        out = capsys.readouterr().out
        assert "Summary by status" in out

    def test_by_priority(self, pm_instance, capsys):
        assert pm_instance.summary(group_by="priority") == 0
        out = capsys.readouterr().out
        assert "Summary by priority" in out
        assert "P0" in out


# ---------------------------------------------------------------------------
# add_story
# ---------------------------------------------------------------------------


class TestAddStory:
    def test_adds_spike(self, backlog_file, capsys):
        pm_inst = ProjectManager(backlog_file)
        assert pm_inst.add_story(
            type="Spike", title="New spike", description="desc",
            points=2, priority="P1", milestone="v0.2.0",
        ) == 0
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        assert len(data["stories"]) == 3
        new = data["stories"][-1]
        assert new["id"] == "SK-002"
        assert new["type"] == "Spike"
        assert new["tasks"] == []
        assert "Added story SK-002" in capsys.readouterr().out

    def test_adds_tech_story(self, backlog_file):
        ProjectManager(backlog_file).add_story(type="Tech", title="Tech story")
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        assert data["stories"][-1]["id"] == "TS-002"

    def test_tdd_defaults_false(self, backlog_file):
        ProjectManager(backlog_file).add_story(type="Tech", title="No TDD")
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        assert data["stories"][-1]["tdd"] is False

    def test_tdd_true(self, backlog_file):
        ProjectManager(backlog_file).add_story(type="Tech", title="TDD story", tdd=True)
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        assert data["stories"][-1]["tdd"] is True

    def test_user_story_prefix(self, backlog_file):
        ProjectManager(backlog_file).add_story(type="User Story", title="As a user")
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        assert data["stories"][-1]["id"] == "US-001"

    def test_bug_prefix(self, backlog_file):
        ProjectManager(backlog_file).add_story(type="Bug", title="Fix crash")
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        assert data["stories"][-1]["id"] == "BG-001"


# ---------------------------------------------------------------------------
# add_task
# ---------------------------------------------------------------------------


class TestAddTask:
    def test_adds_task(self, backlog_file, capsys):
        pm_inst = ProjectManager(backlog_file)
        assert pm_inst.add_task(
            parent_story_id="SK-001", title="New task", description="desc",
            priority="P1", complexity="M", labels=["test"],
        ) == 0
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        sk001 = data["stories"][0]
        assert len(sk001["tasks"]) == 3
        assert sk001["tasks"][-1]["id"] == "T-004"
        assert "Added task T-004" in capsys.readouterr().out

    def test_minimal(self, backlog_file):
        ProjectManager(backlog_file).add_task(parent_story_id="TS-001", title="Minimal")
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        ts001 = next(s for s in data["stories"] if s["id"] == "TS-001")
        assert ts001["tasks"][-1]["status"] == "Backlog"
        assert ts001["tasks"][-1]["priority"] == "P2"

    def test_parent_not_found(self, backlog_file, capsys):
        rc = ProjectManager(backlog_file).add_task(parent_story_id="SK-999", title="X")
        assert rc == 1
        assert "Parent story not found" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateTask:
    def test_status(self, backlog_file, capsys):
        pm_inst = ProjectManager(backlog_file)
        assert pm_inst.update(key="T-001", status="In progress", force=True) == 0
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        assert data["stories"][0]["tasks"][0]["status"] == "In progress"
        assert "Updated T-001" in capsys.readouterr().out

    def test_multiple_fields(self, backlog_file):
        pm_inst = ProjectManager(backlog_file)
        pm_inst.update(key="T-002", status="Done", priority="P0", complexity="L", force=True)
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        t = data["stories"][0]["tasks"][1]
        assert t["status"] == "Done"
        assert t["priority"] == "P0"
        assert t["complexity"] == "L"

    def test_not_found(self, backlog_file, capsys):
        assert ProjectManager(backlog_file).update(key="T-999", status="Done") == 1
        assert "not found" in capsys.readouterr().err

    def test_nothing_to_update(self, backlog_file, capsys):
        assert ProjectManager(backlog_file).update(key="T-001") == 1
        assert "Nothing to update" in capsys.readouterr().err


class TestUpdateStory:
    def test_status(self, backlog_file):
        pm_inst = ProjectManager(backlog_file)
        assert pm_inst.update(key="SK-001", status="Done", force=True) == 0
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        assert data["stories"][0]["status"] == "Done"

    def test_dates(self, backlog_file):
        pm_inst = ProjectManager(backlog_file)
        pm_inst.update(key="TS-001", start_date="2026-03-01", target_date="2026-03-15")
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        ts001 = next(s for s in data["stories"] if s["id"] == "TS-001")
        assert ts001["start_date"] == "2026-03-01"
        assert ts001["target_date"] == "2026-03-15"

    def test_not_found(self, backlog_file, capsys):
        assert ProjectManager(backlog_file).update(key="SK-999", status="Done") == 1
        assert "not found" in capsys.readouterr().err


class TestUpdateGuardrail:
    def test_invalid_blocked(self, backlog_file, capsys):
        assert ProjectManager(backlog_file).update(key="T-003", status="Done") == 1
        assert "Cannot move" in capsys.readouterr().err

    def test_force_bypass(self, backlog_file):
        pm_inst = ProjectManager(backlog_file)
        assert pm_inst.update(key="T-003", status="Done", force=True) == 0
        data = json.loads(backlog_file.read_text(encoding="utf-8"))
        assert data["stories"][1]["tasks"][0]["status"] == "Done"

    def test_valid_passes(self, backlog_file, capsys):
        assert ProjectManager(backlog_file).update(key="T-003", status="In progress") == 0
        assert "Updated T-003" in capsys.readouterr().out

    def test_non_status_no_guardrail(self, backlog_file):
        assert ProjectManager(backlog_file).update(key="T-003", priority="P0") == 0


# ---------------------------------------------------------------------------
# progress
# ---------------------------------------------------------------------------


class TestProgress:
    def test_output(self, pm_instance, capsys):
        assert pm_instance.progress() == 0
        out = capsys.readouterr().out
        assert "Test" in out
        assert "Test goal" in out
        assert "1/3 tasks done" in out
        assert "33%" in out

    def test_story_completion(self, pm_instance, capsys):
        pm_instance.progress()
        out = capsys.readouterr().out
        assert "Story completion:" in out
        assert "0/2 stories done" in out

    def test_per_story(self, pm_instance, capsys):
        pm_instance.progress()
        out = capsys.readouterr().out
        assert "Per-story task completion:" in out
        assert "SK-001" in out
        assert "TS-001" in out

    def test_empty(self, tmp_path, capsys):
        ProjectManager(tmp_path / "backlog.json").progress()
        assert "No tasks" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# unblocked
# ---------------------------------------------------------------------------


SAMPLE_BACKLOG_UNBLOCKED: dict = {
    "project": "T",
    "stories": [
        {
            "id": "SK-001", "type": "Spike", "title": "Story A", "status": "Done",
            "blocked_by": [], "is_blocking": [],
            "tasks": [
                {"id": "T-001", "title": "Task A", "status": "Backlog", "type": "task"},
                {"id": "T-002", "title": "Task B", "status": "Backlog", "type": "task"},
                {"id": "T-003", "title": "Task C", "status": "Done", "type": "task"},
            ],
        },
        {
            "id": "SK-002", "type": "Spike", "title": "Story B", "status": "Backlog",
            "blocked_by": ["SK-001"], "is_blocking": [], "tasks": [],
        },
        {
            "id": "SK-003", "type": "Spike", "title": "Story C", "status": "Backlog",
            "blocked_by": ["SK-002"], "is_blocking": [], "tasks": [],
        },
    ],
}


@pytest.fixture
def unblocked_backlog_file(tmp_path):
    p = tmp_path / "backlog.json"
    p.write_text(json.dumps(SAMPLE_BACKLOG_UNBLOCKED), encoding="utf-8")
    return p


@pytest.fixture
def unblocked_pm(unblocked_backlog_file):
    return ProjectManager(unblocked_backlog_file)


class TestUnblocked:
    def test_correct_items(self, unblocked_pm, capsys):
        # `unblocked` lists stories only — tasks no longer carry blockers.
        assert unblocked_pm.unblocked() == 0
        out = capsys.readouterr().out
        assert "SK-002" in out
        assert "T-001" not in out  # tasks excluded entirely
        assert "T-002" not in out
        assert "T-003" not in out
        assert "SK-001" not in out  # Done
        assert "SK-003" not in out  # blocked by non-Done

    def test_promote(self, unblocked_backlog_file, capsys):
        pm_inst = ProjectManager(unblocked_backlog_file)
        assert pm_inst.unblocked(promote=True) == 0
        data = json.loads(unblocked_backlog_file.read_text(encoding="utf-8"))
        sk002 = data["stories"][1]
        # Only the unblocked story is promoted; tasks are untouched.
        assert sk002["status"] == "Ready"
        assert data["stories"][0]["tasks"][0]["status"] == "Backlog"
        assert data["stories"][0]["tasks"][2]["status"] == "Done"
        assert "Promoted" in capsys.readouterr().out

    def test_promote_skips_already_ready(self, tmp_path, capsys):
        data = {
            "stories": [
                {"id": "SK-001", "status": "Ready", "blocked_by": [], "tasks": []},
            ],
        }
        backlog = tmp_path / "backlog.json"
        backlog.write_text(json.dumps(data), encoding="utf-8")
        ProjectManager(backlog).unblocked(promote=True)
        assert "Promoted 0" in capsys.readouterr().out
        saved = json.loads(backlog.read_text(encoding="utf-8"))
        assert saved["stories"][0]["status"] == "Ready"

    def test_filter_by_story(self, unblocked_pm, capsys):
        # Filtering to a Done parent yields no story matches (stories-only).
        unblocked_pm.unblocked(story="SK-001")
        out = capsys.readouterr().out
        assert "No unblocked items found." in out

    def test_no_items(self, tmp_path, capsys):
        data = {
            "stories": [
                {"id": "SK-001", "status": "Done", "blocked_by": [], "tasks": []},
            ],
        }
        backlog = tmp_path / "backlog.json"
        backlog.write_text(json.dumps(data), encoding="utf-8")
        assert ProjectManager(backlog).unblocked() == 0
        assert "No unblocked items found." in capsys.readouterr().out

    def test_json_output(self, unblocked_pm, capsys):
        assert unblocked_pm.unblocked(json=True) == 0
        parsed = json.loads(capsys.readouterr().out)
        ids = [item["id"] for item in parsed]
        # Only stories appear; tasks are excluded from `unblocked`.
        assert ids == ["SK-002"]
        # `type` is the story type (Spike/Tech/User Story/Bug) — never "task".
        assert all(item["type"] != "task" for item in parsed)
        for item in parsed:
            for req in ("id", "type", "status", "title", "description", "blocked_by"):
                assert req in item

    def test_tasks_excluded_from_listing(self, tmp_path, capsys):
        # Tasks never appear in `unblocked` output — only stories do.
        data = {
            "stories": [
                {"id": "SK-001", "type": "Spike", "title": "Parent",
                 "status": "Ready", "blocked_by": [], "is_blocking": [],
                 "tasks": [
                     {"id": "T-001", "title": "Child", "status": "Backlog",
                      "type": "task"},
                 ]},
            ],
        }
        backlog = tmp_path / "backlog.json"
        backlog.write_text(json.dumps(data), encoding="utf-8")
        pm_inst = ProjectManager(backlog)
        assert pm_inst.unblocked() == 0
        out = capsys.readouterr().out
        assert "T-001" not in out
        # Promote leaves tasks alone (no task promotions occur).
        assert pm_inst.unblocked(promote=True) == 0
        saved = json.loads(backlog.read_text(encoding="utf-8"))
        assert saved["stories"][0]["tasks"][0]["status"] == "Backlog"


# ---------------------------------------------------------------------------
# run() dispatcher
# ---------------------------------------------------------------------------


class TestRun:
    def test_list(self, pm_instance, capsys):
        assert pm_instance.run("list") == 0
        assert "5 task(s)" in capsys.readouterr().out

    def test_ls_alias(self, pm_instance, capsys):
        assert pm_instance.run("ls") == 0
        assert "5 task(s)" in capsys.readouterr().out

    def test_progress(self, pm_instance, capsys):
        assert pm_instance.run("progress") == 0
        assert "Test goal" in capsys.readouterr().out

    def test_view_kwargs(self, pm_instance, capsys):
        assert pm_instance.run("view", key="SK-001", raw=True) == 0
        assert "Research feature X" in capsys.readouterr().out

    def test_unknown_command(self, pm_instance):
        with pytest.raises(ValueError, match="Unknown command"):
            pm_instance.run("does-not-exist")

    def test_sprint_commands_removed(self, pm_instance):
        for cmd in ("create-sprint", "complete-sprint", "sprint-info"):
            with pytest.raises(ValueError):
                pm_instance.run(cmd)
