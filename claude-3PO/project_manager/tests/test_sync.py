"""Tests for project_manager.sync — pure logic, no live API calls."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from project_manager import sync as sp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_created_titles():
    sp._created_titles.clear()


SAMPLE_BACKLOG = {
    "project": "TestProject",
    "goal": "Build foundation",
    "dates": {"start": "2026-02-17", "end": "2026-03-02"},
    "totalPoints": 10,
    "stories": [
        {
            "id": "SK-001",
            "type": "Spike",
            "milestone": "v0.1.0",
            "issue_number": 101,
            "labels": ["spike"],
            "title": "Research features",
            "description": "Research which features to use",
            "points": 3,
            "status": "In progress",
            "start_date": "2026-02-17",
            "target_date": "2026-02-21",
            "priority": "P0",
            "is_blocking": [],
            "blocked_by": [],
            "acceptance_criteria": ["AC1 done", "AC2 done"],
            "tasks": [
                {
                    "id": "T-001",
                    "type": "task",
                    "issue_number": 201,
                    "labels": ["analysis"],
                    "title": "Analyze features",
                    "description": "Perform analysis",
                    "status": "In progress",
                    "priority": "P1",
                    "complexity": "M",
                    "is_blocking": [],
                    "blocked_by": [],
                    "acceptance_criteria": ["Analysis done"],
                },
                {
                    "id": "T-002",
                    "type": "task",
                    "issue_number": 202,
                    "labels": ["docs"],
                    "title": "Document findings",
                    "description": "Write docs",
                    "status": "Ready",
                    "priority": "P2",
                    "complexity": "S",
                    "is_blocking": ["T-001"],
                    "blocked_by": ["T-001"],
                    "acceptance_criteria": ["Docs written"],
                },
            ],
        },
        {
            "id": "TS-002",
            "type": "Tech",
            "milestone": "v0.1.0",
            "issue_number": 102,
            "labels": ["setup"],
            "title": "Setup project",
            "description": "Initialize the project",
            "points": 7,
            "status": "Ready",
            "start_date": "2026-02-24",
            "target_date": "2026-02-28",
            "priority": "P1",
            "is_blocking": ["SK-001"],
            "blocked_by": [],
            "acceptance_criteria": ["Project setup"],
            "tasks": [
                {
                    "id": "T-003",
                    "type": "task",
                    "issue_number": 203,
                    "labels": ["infra"],
                    "title": "Create repo",
                    "description": "Create the repository",
                    "status": "Done",
                    "priority": "P0",
                    "complexity": "S",
                    "is_blocking": [],
                    "blocked_by": [],
                    "acceptance_criteria": ["Repo created"],
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


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestItemFullTitle:
    def test_with_id(self):
        assert sp._item_full_title({"id": "SK-001", "title": "X"}) == "SK-001: X"

    def test_without_id(self):
        assert sp._item_full_title({"title": "X"}) == "X"

    def test_empty_id(self):
        assert sp._item_full_title({"id": "", "title": "X"}) == "X"

    def test_none_id(self):
        assert sp._item_full_title({"id": None, "title": "X"}) == "X"


class TestBuildIssueBody:
    def test_with_criteria(self):
        item = {"description": "Desc", "acceptance_criteria": ["AC1", "AC2"]}
        result = sp.build_issue_body(item)
        assert "Desc" in result
        assert "## Acceptance Criteria" in result
        assert "- [ ] AC1" in result
        assert "- [ ] AC2" in result

    def test_no_criteria(self):
        # No criteria → no header, just the description
        result = sp.build_issue_body({"description": "Just a desc"})
        assert result == "Just a desc"
        assert "Acceptance Criteria" not in result

    def test_empty_description_with_criteria(self):
        result = sp.build_issue_body({"acceptance_criteria": ["AC1"]})
        assert "## Acceptance Criteria" in result
        assert "- [ ] AC1" in result

    def test_both_empty(self):
        assert sp.build_issue_body({"description": "", "acceptance_criteria": []}) == ""

    def test_missing_fields(self):
        assert sp.build_issue_body({}) == ""


# ---------------------------------------------------------------------------
# load_flat_data
# ---------------------------------------------------------------------------


class TestLoadFlatData:
    def test_returns_stories_and_tasks(self, backlog_file):
        stories, tasks, metadata, _ = sp.load_flat_data(backlog_file)
        assert len(stories) == 2
        assert len(tasks) == 3

    def test_stories_tagged(self, backlog_file):
        stories, _, _, _ = sp.load_flat_data(backlog_file)
        assert all(s["item_type"] == "story" for s in stories)

    def test_tasks_tagged_and_have_parent(self, backlog_file):
        _, tasks, _, _ = sp.load_flat_data(backlog_file)
        assert all(t["item_type"] == "task" for t in tasks)
        ids = {t["id"]: t["parent_story_id"] for t in tasks}
        assert ids["T-001"] == "SK-001"
        assert ids["T-002"] == "SK-001"
        assert ids["T-003"] == "TS-002"

    def test_tasks_inherit_story_milestone(self, backlog_file):
        _, tasks, _, _ = sp.load_flat_data(backlog_file)
        assert all(t["milestone"] == "v0.1.0" for t in tasks)

    def test_metadata(self, backlog_file):
        _, _, metadata, _ = sp.load_flat_data(backlog_file)
        assert metadata["project"] == "TestProject"
        assert metadata["goal"] == "Build foundation"
        assert metadata["totalPoints"] == 10
        assert metadata["dates"]["start"] == "2026-02-17"

    def test_returns_raw_backlog(self, backlog_file):
        _, _, _, backlog_data = sp.load_flat_data(backlog_file)
        assert isinstance(backlog_data, dict)
        assert len(backlog_data["stories"]) == 2

    def test_empty_backlog(self, tmp_path):
        p = tmp_path / "b.json"
        p.write_text(json.dumps({"stories": []}), encoding="utf-8")
        stories, tasks, _, _ = sp.load_flat_data(p)
        assert stories == []
        assert tasks == []


# ---------------------------------------------------------------------------
# build_id_to_issue_number_map
# ---------------------------------------------------------------------------


class TestBuildIdToIssueNumberMap:
    def test_maps_all_ids(self):
        stories = [{"id": "A", "issue_number": 1}, {"id": "B", "issue_number": 2}]
        tasks = [{"id": "T1", "issue_number": 10}]
        id_map = sp.build_id_to_issue_number_map(stories, tasks)
        assert id_map == {"A": 1, "B": 2, "T1": 10}

    def test_skips_missing_numbers(self):
        stories = [{"id": "A"}, {"id": "B", "issue_number": 2}]
        id_map = sp.build_id_to_issue_number_map(stories, [])
        assert id_map == {"B": 2}


# ---------------------------------------------------------------------------
# save_flat_data
# ---------------------------------------------------------------------------


class TestSaveFlatData:
    def test_writes_issue_numbers(self, tmp_path):
        p = tmp_path / "b.json"
        backlog = {
            "stories": [
                {"id": "SK-001", "tasks": [{"id": "T-001"}]},
            ],
        }
        p.write_text(json.dumps(backlog), encoding="utf-8")
        _, _, _, backlog_data = sp.load_flat_data(p)
        # Simulate sync assigning issue numbers
        backlog_data["stories"][0]["issue_number"] = 999
        backlog_data["stories"][0]["tasks"][0]["issue_number"] = 1000
        stories, tasks, _, _ = sp.load_flat_data(p)
        # Rebuild with updated refs from our already-loaded data
        sp.save_flat_data(
            [backlog_data["stories"][0]],
            [backlog_data["stories"][0]["tasks"][0]],
            p, backlog_data,
        )
        reloaded = json.loads(p.read_text(encoding="utf-8"))
        assert reloaded["stories"][0]["issue_number"] == 999
        assert reloaded["stories"][0]["tasks"][0]["issue_number"] == 1000

    def test_preserves_other_fields(self, tmp_path, backlog_file):
        stories, tasks, _, backlog_data = sp.load_flat_data(backlog_file)
        sp.save_flat_data(stories, tasks, backlog_file, backlog_data)
        reloaded = json.loads(backlog_file.read_text(encoding="utf-8"))
        assert reloaded["project"] == "TestProject"
        assert reloaded["goal"] == "Build foundation"
        assert reloaded["stories"][0]["title"] == "Research features"


# ---------------------------------------------------------------------------
# set_blocking_relationships
# ---------------------------------------------------------------------------


class TestSetBlockingRelationship:
    @patch.object(sp, "_fetch_node_ids", return_value={100: "NODE-100", 200: "NODE-200"})
    @patch.object(sp, "run")
    def test_calls_addBlockedBy(self, mock_run, mock_fetch):
        items = [{"id": "T-001", "issue_number": 100, "blocked_by": ["SK-001"]}]
        id_map = {"SK-001": 200}
        sp.set_blocking_relationships("org/repo", items, id_map)
        assert any(
            "graphql" in str(c) and "addBlockedBy" in str(c)
            for c in mock_run.call_args_list
        )

    @patch.object(sp, "_fetch_node_ids", return_value={})
    @patch.object(sp, "run")
    def test_skips_empty(self, mock_run, mock_fetch, capsys):
        sp.set_blocking_relationships("org/repo", [], {})
        assert "No blocking" in capsys.readouterr().out
        assert not any("graphql" in str(c) for c in mock_run.call_args_list)

    @patch.object(sp, "_fetch_node_ids", return_value={})
    @patch.object(sp, "run")
    def test_skips_when_node_id_missing(self, mock_run, mock_fetch, capsys):
        items = [{"id": "T-001", "issue_number": 100, "blocked_by": ["SK-001"]}]
        sp.set_blocking_relationships("org/repo", items, {"SK-001": 200})
        err = capsys.readouterr().out
        assert "Missing node ID" in err

    @patch.object(sp, "_fetch_node_ids", return_value={100: "NODE-100"})
    @patch.object(sp, "run")
    def test_skips_unresolved_ids(self, mock_run, mock_fetch):
        items = [{"id": "T-001", "issue_number": 100, "blocked_by": ["MISSING"]}]
        sp.set_blocking_relationships("org/repo", items, {})
        # No mutation run because unresolved id filtered out
        assert not any("addBlockedBy" in str(c) for c in mock_run.call_args_list)


# ---------------------------------------------------------------------------
# resolve_existing_issues
# ---------------------------------------------------------------------------


class TestResolveExistingIssues:
    def test_already_has_issue_number(self):
        tasks = [{"id": "T-001", "title": "X", "issue_number": 42}]
        assert sp.resolve_existing_issues(tasks, {}) == []

    def test_matches_existing_by_title(self):
        tasks = [{"id": "T-001", "title": "X"}]
        existing = {"T-001: X": 99}
        assert sp.resolve_existing_issues(tasks, existing) == []
        assert tasks[0]["issue_number"] == 99

    def test_needs_creation(self):
        tasks = [{"id": "T-001", "title": "New"}]
        needs = sp.resolve_existing_issues(tasks, {})
        assert needs == tasks

    def test_mixed(self):
        tasks = [
            {"id": "T-001", "title": "Has", "issue_number": 1},
            {"id": "T-002", "title": "Needs"},
            {"id": "T-003", "title": "Found"},
        ]
        needs = sp.resolve_existing_issues(tasks, {"T-003: Found": 5})
        assert [t["id"] for t in needs] == ["T-002"]


# ---------------------------------------------------------------------------
# build_field_map / find_item_id / issue_url
# ---------------------------------------------------------------------------


class TestBuildFieldMap:
    def test_basic(self):
        fields = [{"id": "F1", "name": "Status", "type": "TEXT"}]
        fmap = sp.build_field_map(fields)
        assert fmap["Status"]["id"] == "F1"

    def test_with_options(self):
        fields = [{
            "id": "F1", "name": "Status", "type": "SINGLE_SELECT",
            "options": [{"id": "O1", "name": "Done"}, {"id": "O2", "name": "Ready"}],
        }]
        fmap = sp.build_field_map(fields)
        assert fmap["Status"]["options"] == {"Done": "O1", "Ready": "O2"}

    def test_empty(self):
        assert sp.build_field_map([]) == {}

    def test_multiple(self):
        fields = [
            {"id": "F1", "name": "Status"},
            {"id": "F2", "name": "Priority"},
        ]
        fmap = sp.build_field_map(fields)
        assert set(fmap.keys()) == {"Status", "Priority"}


class TestFindItemId:
    def test_found(self):
        items = [{"id": "I1", "content": {"number": 1}}, {"id": "I2", "content": {"number": 2}}]
        assert sp.find_item_id(items, 2) == "I2"

    def test_not_found(self):
        items = [{"id": "I1", "content": {"number": 1}}]
        assert sp.find_item_id(items, 99) is None

    def test_empty(self):
        assert sp.find_item_id([], 1) is None


class TestIssueUrl:
    def test_basic(self):
        assert sp.issue_url("o/r", 42) == "https://github.com/o/r/issues/42"


# ---------------------------------------------------------------------------
# _build_field_value
# ---------------------------------------------------------------------------


class TestBuildFieldValue:
    def test_single_select(self):
        field_map = {"Status": {"id": "F1", "options": {"Done": "O1"}}}
        result = sp._build_field_value(field_map, "Status", "Done")
        assert result == {"singleSelectOptionId": '"O1"'}

    def test_single_select_invalid(self, capsys):
        field_map = {"Status": {"id": "F1", "options": {"Done": "O1"}}}
        result = sp._build_field_value(field_map, "Status", "Invalid")
        assert result is None
        assert "not found" in capsys.readouterr().err

    def test_number(self):
        field_map = {"Points": {"id": "F2"}}
        result = sp._build_field_value(field_map, "Points", 5)
        assert result == {"number": "5"}

    def test_date(self):
        field_map = {"Start date": {"id": "F3"}}
        result = sp._build_field_value(field_map, "Start date", "2026-01-01")
        assert result == {"date": '"2026-01-01"'}

    def test_text(self):
        field_map = {"Notes": {"id": "F4"}}
        result = sp._build_field_value(field_map, "Notes", "hello")
        assert result == {"text": '"hello"'}

    def test_none_value(self):
        field_map = {"Notes": {"id": "F4"}}
        assert sp._build_field_value(field_map, "Notes", None) is None

    def test_empty_value(self):
        field_map = {"Notes": {"id": "F4"}}
        assert sp._build_field_value(field_map, "Notes", "") is None

    def test_field_not_found(self):
        assert sp._build_field_value({}, "Missing", "val") is None


# ---------------------------------------------------------------------------
# _collect_mutations
# ---------------------------------------------------------------------------


class TestCollectMutations:
    def test_story_gets_points_not_complexity(self):
        story = {
            "id": "SK-001", "item_type": "story", "issue_number": 1,
            "status": "In progress", "priority": "P0", "points": 3,
        }
        items = [{"id": "ITEM-1", "content": {"number": 1}}]
        field_map = {
            "Status": {"id": "FS", "options": {"In progress": "OS"}},
            "Priority": {"id": "FP", "options": {"P0": "OP"}},
            "Points": {"id": "FPts"},
            "Complexity": {"id": "FC", "options": {"M": "OM"}},
            "Start date": {"id": "FSD"},
            "Target date": {"id": "FTD"},
        }
        mutations = sp._collect_mutations([story], items, "PID", field_map)
        flat = " ".join(mutations)
        assert "FPts" in flat
        assert "FC" not in flat

    def test_task_gets_complexity_not_points(self):
        task = {
            "id": "T-001", "item_type": "task", "issue_number": 2,
            "status": "Ready", "priority": "P1", "complexity": "M",
        }
        items = [{"id": "ITEM-2", "content": {"number": 2}}]
        field_map = {
            "Status": {"id": "FS", "options": {"Ready": "OS"}},
            "Priority": {"id": "FP", "options": {"P1": "OP"}},
            "Points": {"id": "FPts"},
            "Complexity": {"id": "FC", "options": {"M": "OM"}},
            "Start date": {"id": "FSD"},
            "Target date": {"id": "FTD"},
        }
        mutations = sp._collect_mutations([task], items, "PID", field_map)
        flat = " ".join(mutations)
        assert "FC" in flat
        assert "FPts" not in flat

    def test_empty(self):
        assert sp._collect_mutations([], [], "PID", {}) == []


# ---------------------------------------------------------------------------
# _create_issue
# ---------------------------------------------------------------------------


class TestCreateIssue:
    @patch.object(sp, "run", return_value="https://github.com/org/repo/issues/5")
    @patch.object(sp, "ensure_label")
    def test_returns_number(self, mock_label, mock_run):
        task = {"id": "T-001", "title": "New", "labels": [], "type": "task"}
        assert sp._create_issue(task, "org/repo") == 5
        assert task["issue_number"] == 5

    @patch.object(sp, "run", return_value="https://github.com/org/repo/issues/1")
    @patch.object(sp, "ensure_label")
    def test_dedup_guard(self, mock_label, mock_run):
        task1 = {"id": "T-001", "title": "X"}
        task2 = {"id": "T-001", "title": "X"}
        sp._create_issue(task1, "org/repo")
        with pytest.raises(RuntimeError, match="Duplicate"):
            sp._create_issue(task2, "org/repo")

    @patch.object(sp, "run", return_value="https://github.com/org/repo/issues/1")
    @patch.object(sp, "ensure_label")
    def test_appends_type_as_label(self, mock_label, mock_run):
        task = {"id": "T-001", "title": "X", "type": "Spike", "labels": []}
        sp._create_issue(task, "org/repo")
        cmd = mock_run.call_args[0][0]
        assert "spike" in cmd
        assert "Spike" not in cmd

    @patch.object(sp, "run", return_value="https://github.com/org/repo/issues/1")
    @patch.object(sp, "ensure_label")
    def test_lowercases_labels_and_type(self, mock_label, mock_run):
        task = {"id": "T-002", "title": "X", "type": "Spike", "labels": ["Infra"]}
        sp._create_issue(task, "org/repo")
        cmd = mock_run.call_args[0][0]
        assert "spike" in cmd
        assert "infra" in cmd
        assert "Spike" not in cmd
        assert "Infra" not in cmd

    @patch.object(sp, "run", return_value="https://github.com/org/repo/issues/1")
    @patch.object(sp, "ensure_label")
    def test_does_not_duplicate_label(self, mock_label, mock_run):
        task = {"id": "T-003", "title": "X", "type": "Spike", "labels": ["spike"]}
        sp._create_issue(task, "org/repo")
        cmd = mock_run.call_args[0][0]
        assert cmd.count("spike") == 1

    @patch.object(sp, "run", return_value="")
    @patch.object(sp, "ensure_label")
    def test_raises_on_empty_url(self, mock_label, mock_run):
        task = {"id": "T-001", "title": "X"}
        with pytest.raises(RuntimeError, match="returned no URL"):
            sp._create_issue(task, "org/repo")


# ---------------------------------------------------------------------------
# ensure_issue
# ---------------------------------------------------------------------------


class TestEnsureIssue:
    def test_returns_existing_number(self):
        task = {"id": "T", "title": "X", "issue_number": 5}
        assert sp.ensure_issue(task, "org/repo") == 5

    def test_uses_cache(self):
        task = {"id": "T", "title": "X"}
        assert sp.ensure_issue(task, "org/repo", {"T: X": 10}) == 10

    @patch.object(sp, "find_existing_issue", return_value=20)
    def test_fallback_search(self, mock_find):
        task = {"id": "T", "title": "X"}
        assert sp.ensure_issue(task, "org/repo", {}) == 20

    @patch.object(sp, "find_existing_issue", return_value=None)
    @patch.object(sp, "_create_issue", return_value=30)
    def test_creates_if_not_found(self, mock_create, mock_find):
        task = {"id": "T", "title": "X"}
        assert sp.ensure_issue(task, "org/repo", {}) == 30


# ---------------------------------------------------------------------------
# execute_batched_mutations
# ---------------------------------------------------------------------------


class TestExecuteBatchedMutations:
    def test_empty(self, capsys):
        sp.execute_batched_mutations([])
        assert "No field updates" in capsys.readouterr().out

    @patch("subprocess.run")
    def test_single_batch(self, mock_run, capsys):
        mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "{}", "stderr": ""})()
        mutations = [f"m{i}: stub" for i in range(5)]
        sp.execute_batched_mutations(mutations)
        out = capsys.readouterr().out
        assert "5 field updates" in out
        assert "Batch 1/1" in out

    @patch("subprocess.run")
    def test_multiple_batches(self, mock_run, capsys):
        mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "{}", "stderr": ""})()
        mutations = [f"m{i}: stub" for i in range(35)]
        sp.execute_batched_mutations(mutations)
        out = capsys.readouterr().out
        assert "Batch 1/2" in out
        assert "Batch 2/2" in out


# ---------------------------------------------------------------------------
# set_field
# ---------------------------------------------------------------------------


class TestSetField:
    @patch.object(sp, "run")
    def test_single_select(self, mock_run):
        field_map = {"Status": {"id": "F1", "options": {"Done": "OPT1"}}}
        sp.set_field("PID", "ITEM", field_map, "Status", "Done")
        cmd = mock_run.call_args[0][0]
        assert "--single-select-option-id" in cmd
        assert "OPT1" in cmd

    @patch.object(sp, "run")
    def test_number(self, mock_run):
        sp.set_field("PID", "ITEM", {"Points": {"id": "F2"}}, "Points", 5)
        assert "--number" in mock_run.call_args[0][0]

    @patch.object(sp, "run")
    def test_date(self, mock_run):
        sp.set_field("PID", "ITEM", {"Start date": {"id": "F3"}}, "Start date", "2026-01-01")
        assert "--date" in mock_run.call_args[0][0]

    def test_none_value(self):
        sp.set_field("PID", "ITEM", {}, "Status", None)  # no raise

    def test_empty_value(self):
        sp.set_field("PID", "ITEM", {}, "Status", "")  # no raise

    def test_field_not_found(self, capsys):
        sp.set_field("PID", "ITEM", {}, "Missing", "val")
        assert "not found" in capsys.readouterr().err

    def test_invalid_option(self, capsys):
        field_map = {"Status": {"id": "F1", "options": {"Done": "OPT1"}}}
        sp.set_field("PID", "ITEM", field_map, "Status", "Invalid")
        assert "not found" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Syncer class
# ---------------------------------------------------------------------------


class TestSyncerClass:
    def test_init_defaults(self):
        s = sp.Syncer()
        assert s.backlog_path is not None
        assert s.repo is not None

    def test_init_with_overrides(self, tmp_path):
        s = sp.Syncer(backlog_path=tmp_path / "b.json", repo="o/r", project=7, owner="me")
        assert s.backlog_path == tmp_path / "b.json"
        assert s.repo == "o/r"
        assert s.project == 7
        assert s.owner == "me"

    def test_run_unknown_mode(self, tmp_path):
        s = sp.Syncer(backlog_path=tmp_path / "b.json")
        with pytest.raises(ValueError, match="Unknown sync mode"):
            s.run("not-a-mode")

    def test_delete_all_aliases(self, tmp_path):
        # Both dashed and underscore forms should dispatch to delete_all
        assert "delete-all" in sp.Syncer._MODE_MAP
        assert "delete_all" in sp.Syncer._MODE_MAP


# ---------------------------------------------------------------------------
# _apply_sync_scope
# ---------------------------------------------------------------------------


class TestApplySyncScope:
    def test_all(self):
        s, t = sp._apply_sync_scope([{"id": "A"}], [{"id": "T"}], "all")
        assert s and t

    def test_stories_only(self):
        s, t = sp._apply_sync_scope([{"id": "A"}], [{"id": "T"}], "stories")
        assert s == [{"id": "A"}]
        assert t == []

    def test_tasks_only(self):
        s, t = sp._apply_sync_scope([{"id": "A"}], [{"id": "T"}], "tasks")
        assert s == []
        assert t == [{"id": "T"}]
