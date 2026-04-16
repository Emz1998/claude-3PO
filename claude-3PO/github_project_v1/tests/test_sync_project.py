"""Tests for sync_project.py — pure logic tests, no API calls."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sync_project as sp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_created_titles():
    """Reset the dedup guard between tests."""
    sp._created_titles.clear()


SAMPLE_STORIES_DATA = {
    "project": "TestProject",
    "goal": "Build foundation",
    "dates": {"start": "2026-02-17", "end": "2026-03-02"},
    "totalPoints": 10,
    "stories": [
        {
            "id": "SK-001",
            "type": "Spike",
            "issue_number": 101,
            "labels": ["spike"],
            "title": "Research features",
            "description": "Research which features to use",
            "points": 3,
            "status": "In progress",
            "startDate": "2026-02-17",
            "targetDate": "2026-02-21",
            "priority": "P0",
            "is_blocking": [],
            "blocked_by": [],
            "acceptance_criteria": ["AC1 done", "AC2 done"],
        },
        {
            "id": "TS-002",
            "type": "Tech",
            "issue_number": 102,
            "labels": ["setup"],
            "title": "Setup project",
            "description": "Initialize the project",
            "points": 7,
            "status": "Ready",
            "startDate": "2026-02-24",
            "targetDate": "2026-02-28",
            "priority": "P1",
            "is_blocking": ["SK-001"],
            "blocked_by": [],
            "acceptance_criteria": ["Project setup"],
        },
    ],
}

SAMPLE_SPRINT_DATA = {
    "sprint": 1,
    "milestone": "v0.1.0",
    "description": "Build foundation",
    "due_date": "2026-03-02",
    "tasks": [
        {
            "id": "T-001",
            "type": "task",
            "parent_story_id": "SK-001",
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
            "parent_story_id": "SK-001",
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
        {
            "id": "T-003",
            "type": "task",
            "parent_story_id": "TS-002",
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
}


@pytest.fixture
def flat_files(tmp_path):
    """Write sample flat files and return (stories_path, sprint_path)."""
    stories_path = tmp_path / "stories.json"
    sprint_path = tmp_path / "sprint.json"
    stories_path.write_text(json.dumps(SAMPLE_STORIES_DATA), encoding="utf-8")
    sprint_path.write_text(json.dumps(SAMPLE_SPRINT_DATA), encoding="utf-8")
    return stories_path, sprint_path


# ---------------------------------------------------------------------------
# _item_full_title
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


# ---------------------------------------------------------------------------
# build_issue_body
# ---------------------------------------------------------------------------


class TestBuildIssueBody:
    def test_with_criteria(self):
        item = {
            "description": "Some desc",
            "acceptance_criteria": ["AC1", "AC2"],
        }
        result = sp.build_issue_body(item)
        assert result == "Some desc\n\n- [ ] AC1\n- [ ] AC2"

    def test_no_criteria(self):
        item = {"description": "Just a desc", "acceptance_criteria": []}
        assert sp.build_issue_body(item) == "Just a desc"

    def test_empty_description_with_criteria(self):
        item = {"description": "", "acceptance_criteria": ["AC1"]}
        assert sp.build_issue_body(item) == "- [ ] AC1"

    def test_both_empty(self):
        item = {"description": "", "acceptance_criteria": []}
        assert sp.build_issue_body(item) == ""

    def test_missing_fields(self):
        assert sp.build_issue_body({}) == ""


# ---------------------------------------------------------------------------
# load_flat_data
# ---------------------------------------------------------------------------


class TestLoadFlatData:
    def test_returns_stories_and_tasks(self, flat_files):
        stories, tasks, metadata, _, _ = sp.load_flat_data(*flat_files)
        assert len(stories) == 2
        assert len(tasks) == 3

    def test_story_fields(self, flat_files):
        stories, tasks, metadata, _, _ = sp.load_flat_data(*flat_files)
        s = stories[0]
        assert s["id"] == "SK-001"
        assert s["type"] == "Spike"
        assert s["points"] == 3
        assert s["startDate"] == "2026-02-17"
        assert s["targetDate"] == "2026-02-21"
        assert s["priority"] == "P0"
        assert s["status"] == "In progress"
        assert s["is_blocking"] == []
        assert s["blocked_by"] == []
        assert s["acceptance_criteria"] == ["AC1 done", "AC2 done"]
        assert s["item_type"] == "story"

    def test_task_fields(self, flat_files):
        stories, tasks, metadata, _, _ = sp.load_flat_data(*flat_files)
        t = tasks[0]
        assert t["id"] == "T-001"
        assert t["type"] == "task"
        assert t["complexity"] == "M"
        assert t["priority"] == "P1"
        assert t["status"] == "In progress"
        assert t["parent_story_id"] == "SK-001"
        assert t["item_type"] == "task"

    def test_metadata_extraction(self, flat_files):
        stories, tasks, metadata, _, _ = sp.load_flat_data(*flat_files)
        assert metadata["milestone"] == "v0.1.0"
        assert metadata["sprint"] == 1
        assert metadata["goal"] == "Build foundation"
        assert metadata["dates"]["start"] == "2026-02-17"
        assert metadata["dates"]["end"] == "2026-03-02"

    def test_returns_raw_data_dicts(self, flat_files):
        _, _, _, stories_data, sprint_data = sp.load_flat_data(*flat_files)
        assert stories_data["project"] == "TestProject"
        assert sprint_data["sprint"] == 1

    def test_empty_files(self, tmp_path):
        stories_path = tmp_path / "stories.json"
        sprint_path = tmp_path / "sprint.json"
        stories_path.write_text(json.dumps({"stories": []}), encoding="utf-8")
        sprint_path.write_text(json.dumps({"tasks": []}), encoding="utf-8")
        stories, tasks, metadata, _, _ = sp.load_flat_data(stories_path, sprint_path)
        assert stories == []
        assert tasks == []


# ---------------------------------------------------------------------------
# build_id_to_issue_number_map
# ---------------------------------------------------------------------------


class TestBuildIdToIssueNumberMap:
    def test_maps_all_ids(self):
        stories = [{"id": "SK-001", "issue_number": 101}]
        tasks = [
            {"id": "T-001", "issue_number": 201},
            {"id": "T-002", "issue_number": 202},
        ]
        id_map = sp.build_id_to_issue_number_map(stories, tasks)
        assert id_map == {"SK-001": 101, "T-001": 201, "T-002": 202}

    def test_skips_missing_numbers(self):
        stories = [{"id": "SK-001"}]
        tasks = [{"id": "T-001", "issue_number": 201}]
        id_map = sp.build_id_to_issue_number_map(stories, tasks)
        assert id_map == {"T-001": 201}
        assert "SK-001" not in id_map


# ---------------------------------------------------------------------------
# _collect_mutations (v2 — Points/Complexity)
# ---------------------------------------------------------------------------


class TestCollectMutationsV2:
    def test_story_gets_points_not_complexity(self):
        items_data = [{"id": "ITEM-1", "content": {"number": 101}}]
        field_map = {
            "Status": {"id": "F1", "options": {"In progress": "OPT1"}},
            "Priority": {"id": "F2", "options": {"P0": "OPT2"}},
            "Points": {"id": "F3"},
            "Complexity": {"id": "F4", "options": {"M": "OPT3"}},
        }
        story = {
            "issue_number": 101,
            "status": "In progress",
            "priority": "P0",
            "points": 3,
            "complexity": "",
            "start_date": "",
            "target_date": "",
            "item_type": "story",
        }
        mutations = sp._collect_mutations([story], items_data, "PID", field_map)
        mutation_str = " ".join(mutations)
        assert "F3" in mutation_str  # Points field
        assert "OPT3" not in mutation_str  # Complexity option not used

    def test_task_gets_complexity_not_points(self):
        items_data = [{"id": "ITEM-1", "content": {"number": 201}}]
        field_map = {
            "Status": {"id": "F1", "options": {"In progress": "OPT1"}},
            "Priority": {"id": "F2", "options": {"P1": "OPT2"}},
            "Points": {"id": "F3"},
            "Complexity": {"id": "F4", "options": {"M": "OPT3"}},
        }
        task = {
            "issue_number": 201,
            "status": "In progress",
            "priority": "P1",
            "points": "",
            "complexity": "M",
            "start_date": "",
            "target_date": "",
            "item_type": "task",
        }
        mutations = sp._collect_mutations([task], items_data, "PID", field_map)
        mutation_str = " ".join(mutations)
        assert "OPT3" in mutation_str  # Complexity option used


# ---------------------------------------------------------------------------
# save_flat_data
# ---------------------------------------------------------------------------


class TestSaveFlatData:
    def test_writes_issue_numbers_to_both_files(self, tmp_path):
        stories_path = tmp_path / "stories.json"
        sprint_path = tmp_path / "sprint.json"
        stories_data = {
            "project": "Test",
            "stories": [{"id": "SK-001", "title": "Story"}],
        }
        sprint_data = {
            "sprint": 1,
            "tasks": [{"id": "T-001", "title": "Task", "parent_story_id": "SK-001"}],
        }
        stories_path.write_text(json.dumps(stories_data), encoding="utf-8")
        sprint_path.write_text(json.dumps(sprint_data), encoding="utf-8")

        stories = [{"id": "SK-001", "issue_number": 101, "item_type": "story"}]
        tasks = [{"id": "T-001", "issue_number": 201, "item_type": "task"}]

        sp.save_flat_data(stories, tasks, stories_path, sprint_path, stories_data, sprint_data)

        loaded_stories = json.loads(stories_path.read_text())
        loaded_sprint = json.loads(sprint_path.read_text())
        assert loaded_stories["stories"][0]["issue_number"] == 101
        assert loaded_sprint["tasks"][0]["issue_number"] == 201

    def test_preserves_other_fields(self, tmp_path):
        stories_path = tmp_path / "stories.json"
        sprint_path = tmp_path / "sprint.json"
        stories_data = {
            "project": "Test",
            "goal": "Build it",
            "stories": [{"id": "SK-001", "title": "Story", "points": 3}],
        }
        sprint_data = {
            "sprint": 1,
            "milestone": "v0.1.0",
            "tasks": [{"id": "T-001", "title": "Task", "complexity": "M"}],
        }
        stories_path.write_text(json.dumps(stories_data), encoding="utf-8")
        sprint_path.write_text(json.dumps(sprint_data), encoding="utf-8")

        stories = [{"id": "SK-001", "issue_number": 101, "item_type": "story"}]
        tasks = [{"id": "T-001", "issue_number": 201, "item_type": "task"}]

        sp.save_flat_data(stories, tasks, stories_path, sprint_path, stories_data, sprint_data)

        loaded_stories = json.loads(stories_path.read_text())
        loaded_sprint = json.loads(sprint_path.read_text())
        assert loaded_stories["project"] == "Test"
        assert loaded_stories["goal"] == "Build it"
        assert loaded_stories["stories"][0]["points"] == 3
        assert loaded_sprint["milestone"] == "v0.1.0"
        assert loaded_sprint["tasks"][0]["complexity"] == "M"


# ---------------------------------------------------------------------------
# set_blocking_relationships (mocked run)
# ---------------------------------------------------------------------------


class TestSetBlockingRelationship:
    @patch.object(sp, "_get_issue_node_id")
    @patch.object(sp, "run")
    def test_calls_addBlockedBy_mutation(self, mock_run, mock_node_id):
        mock_node_id.side_effect = lambda repo, num: f"NODE_{num}"
        items = [{"id": "T-002", "issue_number": 202, "blocked_by": ["T-001"], "is_blocking": []}]
        id_map = {"T-001": 201, "T-002": 202}
        sp.set_blocking_relationships("org/repo", items, id_map)
        # Should call run once for the GraphQL mutation
        assert mock_run.call_count == 1
        call_args = mock_run.call_args[0][0]
        assert "graphql" in call_args
        query = [a for a in call_args if "addBlockedBy" in a]
        assert len(query) == 1
        assert "NODE_202" in query[0]  # issueId (blocked)
        assert "NODE_201" in query[0]  # blockingIssueId (blocker)

    @patch.object(sp, "_get_issue_node_id")
    @patch.object(sp, "run")
    def test_skips_empty_relationships(self, mock_run, mock_node_id):
        items = [{"id": "T-001", "issue_number": 201, "blocked_by": [], "is_blocking": []}]
        id_map = {"T-001": 201}
        sp.set_blocking_relationships("org/repo", items, id_map)
        mock_run.assert_not_called()
        mock_node_id.assert_not_called()

    @patch.object(sp, "_get_issue_node_id")
    @patch.object(sp, "run")
    def test_skips_unresolved_ids(self, mock_run, mock_node_id):
        items = [{"id": "T-002", "issue_number": 202, "blocked_by": ["T-999"], "is_blocking": []}]
        id_map = {"T-002": 202}  # T-999 not in map
        sp.set_blocking_relationships("org/repo", items, id_map)
        mock_run.assert_not_called()
        mock_node_id.assert_not_called()

    @patch.object(sp, "_get_issue_node_id")
    @patch.object(sp, "run")
    def test_multiple_blocked_by(self, mock_run, mock_node_id):
        mock_node_id.side_effect = lambda repo, num: f"NODE_{num}"
        items = [{"id": "T-003", "issue_number": 203, "blocked_by": ["T-001", "T-002"], "is_blocking": []}]
        id_map = {"T-001": 201, "T-002": 202, "T-003": 203}
        sp.set_blocking_relationships("org/repo", items, id_map)
        # Two addBlockedBy mutations
        assert mock_run.call_count == 2

    @patch.object(sp, "_get_issue_node_id")
    @patch.object(sp, "run")
    def test_only_processes_blocked_by_not_is_blocking(self, mock_run, mock_node_id):
        mock_node_id.side_effect = lambda repo, num: f"NODE_{num}"
        # Item only has is_blocking, no blocked_by — should not create any mutations
        items = [{"id": "T-001", "issue_number": 201, "is_blocking": ["T-002"], "blocked_by": []}]
        id_map = {"T-001": 201, "T-002": 202}
        sp.set_blocking_relationships("org/repo", items, id_map)
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# resolve_existing_issues (updated for colon format)
# ---------------------------------------------------------------------------


class TestResolveExistingIssues:
    def test_already_has_issue_number(self):
        tasks = [{"title": "Task A", "issue_number": 42}]
        needs = sp.resolve_existing_issues(tasks, {})
        assert needs == []
        assert tasks[0]["issue_number"] == 42

    def test_matches_existing_by_title(self):
        tasks = [{"id": "TS-001", "title": "Do thing"}]
        existing = {"TS-001: Do thing": 10}
        needs = sp.resolve_existing_issues(tasks, existing)
        assert needs == []
        assert tasks[0]["issue_number"] == 10

    def test_needs_creation(self):
        tasks = [{"id": "TS-001", "title": "New task"}]
        needs = sp.resolve_existing_issues(tasks, {})
        assert len(needs) == 1
        assert needs[0] is tasks[0]

    def test_mixed(self):
        tasks = [
            {"id": "TS-001", "title": "Existing", "issue_number": 1},
            {"id": "TS-002", "title": "Matched"},
            {"id": "TS-003", "title": "Brand new"},
        ]
        existing = {"TS-002: Matched": 5}
        needs = sp.resolve_existing_issues(tasks, existing)
        assert len(needs) == 1
        assert needs[0]["id"] == "TS-003"
        assert tasks[1]["issue_number"] == 5


# ---------------------------------------------------------------------------
# build_field_map
# ---------------------------------------------------------------------------


class TestBuildFieldMap:
    def test_basic_field(self):
        fields = [{"id": "F1", "name": "Title", "type": "TEXT"}]
        fmap = sp.build_field_map(fields)
        assert fmap["Title"]["id"] == "F1"
        assert fmap["Title"]["type"] == "TEXT"

    def test_field_with_options(self):
        fields = [{
            "id": "F2",
            "name": "Status",
            "type": "SINGLE_SELECT",
            "options": [
                {"name": "Done", "id": "OPT1"},
                {"name": "Ready", "id": "OPT2"},
            ],
        }]
        fmap = sp.build_field_map(fields)
        assert fmap["Status"]["options"]["Done"] == "OPT1"
        assert fmap["Status"]["options"]["Ready"] == "OPT2"

    def test_empty_fields(self):
        assert sp.build_field_map([]) == {}

    def test_multiple_fields(self):
        fields = [
            {"id": "F1", "name": "Title", "type": "TEXT"},
            {"id": "F2", "name": "Priority", "type": "SINGLE_SELECT",
             "options": [{"name": "P0", "id": "O1"}]},
        ]
        fmap = sp.build_field_map(fields)
        assert len(fmap) == 2
        assert "Title" in fmap
        assert "Priority" in fmap


# ---------------------------------------------------------------------------
# find_item_id
# ---------------------------------------------------------------------------


class TestFindItemId:
    def test_found(self):
        items = [
            {"id": "ITEM-A", "content": {"number": 1}},
            {"id": "ITEM-B", "content": {"number": 2}},
        ]
        assert sp.find_item_id(items, 2) == "ITEM-B"

    def test_not_found(self):
        items = [{"id": "ITEM-A", "content": {"number": 1}}]
        assert sp.find_item_id(items, 99) is None

    def test_empty(self):
        assert sp.find_item_id([], 1) is None

    def test_missing_content(self):
        items = [{"id": "ITEM-A"}]
        assert sp.find_item_id(items, 1) is None


# ---------------------------------------------------------------------------
# issue_url
# ---------------------------------------------------------------------------


class TestIssueUrl:
    def test_basic(self):
        assert sp.issue_url("owner/repo", 42) == "https://github.com/owner/repo/issues/42"


# ---------------------------------------------------------------------------
# _build_field_value
# ---------------------------------------------------------------------------


class TestBuildFieldValue:
    def test_single_select(self):
        field_map = {
            "Status": {"id": "F1", "options": {"Done": "OPT1"}},
        }
        result = sp._build_field_value(field_map, "Status", "Done")
        assert result is not None
        assert "singleSelectOptionId" in result

    def test_single_select_invalid_option(self, capsys):
        field_map = {
            "Status": {"id": "F1", "options": {"Done": "OPT1"}},
        }
        result = sp._build_field_value(field_map, "Status", "Invalid")
        assert result is None

    def test_number_value(self):
        field_map = {"Points": {"id": "F2"}}
        result = sp._build_field_value(field_map, "Points", 5)
        assert result == {"number": "5"}

    def test_date_value(self):
        field_map = {"Start date": {"id": "F3"}}
        result = sp._build_field_value(field_map, "Start date", "2026-01-01")
        assert result is not None
        assert "date" in result

    def test_text_value(self):
        field_map = {"Notes": {"id": "F4"}}
        result = sp._build_field_value(field_map, "Notes", "hello")
        assert result is not None
        assert "text" in result

    def test_none_value(self):
        field_map = {"Notes": {"id": "F4"}}
        assert sp._build_field_value(field_map, "Notes", None) is None

    def test_empty_value(self):
        field_map = {"Notes": {"id": "F4"}}
        assert sp._build_field_value(field_map, "Notes", "") is None

    def test_field_not_found(self, capsys):
        assert sp._build_field_value({}, "Missing", "val") is None


# ---------------------------------------------------------------------------
# _collect_mutations (legacy format still works)
# ---------------------------------------------------------------------------


class TestCollectMutations:
    def test_basic_mutations(self):
        tasks = [{
            "issue_number": 1,
            "status": "Done",
            "priority": "P0",
            "points": "",
            "complexity": "",
            "start_date": "",
            "target_date": "",
            "item_type": "story",
        }]
        items = [{"id": "ITEM-1", "content": {"number": 1}}]
        field_map = {
            "Status": {"id": "F1", "options": {"Done": "OPT1"}},
            "Priority": {"id": "F2", "options": {"P0": "OPT2"}},
        }
        mutations = sp._collect_mutations(tasks, items, "PID", field_map)
        assert len(mutations) == 2
        assert "updateProjectV2ItemFieldValue" in mutations[0]

    def test_no_matching_item(self, capsys):
        tasks = [{"issue_number": 99, "status": "Done", "priority": "", "points": "",
                  "complexity": "", "start_date": "", "target_date": "", "item_type": "story"}]
        items = [{"id": "ITEM-1", "content": {"number": 1}}]
        field_map = {"Status": {"id": "F1", "options": {"Done": "OPT1"}}}
        mutations = sp._collect_mutations(tasks, items, "PID", field_map)
        assert len(mutations) == 0

    def test_empty_tasks(self):
        mutations = sp._collect_mutations([], [], "PID", {})
        assert mutations == []


# ---------------------------------------------------------------------------
# _create_issue (mocked, updated for colon format)
# ---------------------------------------------------------------------------


class TestCreateIssue:
    @patch.object(sp, "run", return_value="https://github.com/org/repo/issues/42")
    @patch.object(sp, "ensure_label")
    def test_creates_and_returns_number(self, mock_label, mock_run):
        task = {"id": "TS-001", "title": "New task", "labels": ["bug"], "assignees": ["alice"]}
        num = sp._create_issue(task, "org/repo")
        assert num == 42
        assert task["issue_number"] == 42
        mock_label.assert_called_once_with("bug", "org/repo")
        # Verify colon format in title
        call_args = mock_run.call_args[0][0]
        assert "TS-001: New task" in call_args

    @patch.object(sp, "run", return_value="https://github.com/org/repo/issues/43")
    @patch.object(sp, "ensure_label")
    def test_dedup_guard(self, mock_label, mock_run):
        task1 = {"id": "TS-001", "title": "Same title"}
        task2 = {"id": "TS-001", "title": "Same title"}
        sp._create_issue(task1, "org/repo")
        with pytest.raises(RuntimeError, match="Duplicate title"):
            sp._create_issue(task2, "org/repo")

    @patch.object(sp, "run", return_value="https://github.com/org/repo/issues/44")
    @patch.object(sp, "ensure_label")
    def test_type_appended_as_label(self, mock_label, mock_run):
        task = {"id": "TS-020", "title": "Typed task", "type": "Spike", "labels": ["bug"]}
        sp._create_issue(task, "org/repo")
        call_args = mock_run.call_args[0][0]
        label_args = [call_args[i + 1] for i, v in enumerate(call_args) if v == "--label"]
        assert "bug" in label_args
        assert "Spike" in label_args
        # ensure_label called for both
        assert mock_label.call_count == 2

    @patch.object(sp, "run", return_value="https://github.com/org/repo/issues/45")
    @patch.object(sp, "ensure_label")
    def test_type_not_duplicated_if_already_in_labels(self, mock_label, mock_run):
        task = {"id": "TS-021", "title": "Already labeled", "type": "bug", "labels": ["bug"]}
        sp._create_issue(task, "org/repo")
        call_args = mock_run.call_args[0][0]
        label_args = [call_args[i + 1] for i, v in enumerate(call_args) if v == "--label"]
        assert label_args.count("bug") == 1

    @patch.object(sp, "run", return_value="")
    @patch.object(sp, "ensure_label")
    def test_empty_url_raises(self, mock_label, mock_run):
        task = {"id": "TS-010", "title": "Empty URL task"}
        with pytest.raises(RuntimeError, match="no URL"):
            sp._create_issue(task, "org/repo")


# ---------------------------------------------------------------------------
# ensure_issue (mocked, updated for colon format)
# ---------------------------------------------------------------------------


class TestEnsureIssue:
    def test_already_has_number(self):
        task = {"title": "Task", "issue_number": 5}
        assert sp.ensure_issue(task, "org/repo") == 5

    def test_found_in_cache(self):
        task = {"id": "TS-001", "title": "Cached"}
        existing = {"TS-001: Cached": 10}
        assert sp.ensure_issue(task, "org/repo", existing) == 10
        assert task["issue_number"] == 10

    @patch.object(sp, "find_existing_issue", return_value=20)
    def test_found_via_search(self, mock_find):
        task = {"id": "TS-002", "title": "Searched"}
        assert sp.ensure_issue(task, "org/repo", {}) == 20
        assert task["issue_number"] == 20

    @patch.object(sp, "find_existing_issue", return_value=None)
    @patch.object(sp, "_create_issue", return_value=30)
    def test_creates_new(self, mock_create, mock_find):
        task = {"id": "TS-003", "title": "Brand new"}
        assert sp.ensure_issue(task, "org/repo", {}) == 30


# ---------------------------------------------------------------------------
# execute_batched_mutations (mocked)
# ---------------------------------------------------------------------------


class TestExecuteBatchedMutations:
    def test_empty_mutations(self, capsys):
        sp.execute_batched_mutations([])
        assert "No field updates" in capsys.readouterr().out

    @patch("subprocess.run")
    def test_single_batch(self, mock_run, capsys):
        mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "{}", "stderr": ""})()
        mutations = [f"m{i}: updateProjectV2ItemFieldValue(input: {{}}) {{ projectV2Item {{ id }} }}"
                     for i in range(5)]
        sp.execute_batched_mutations(mutations)
        out = capsys.readouterr().out
        assert "5 field updates" in out
        assert "Batch 1/1" in out

    @patch("subprocess.run")
    def test_multiple_batches(self, mock_run, capsys):
        mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "{}", "stderr": ""})()
        mutations = [f"m{i}: updateProjectV2ItemFieldValue(input: {{}}) {{ projectV2Item {{ id }} }}"
                     for i in range(35)]
        sp.execute_batched_mutations(mutations)
        out = capsys.readouterr().out
        assert "Batch 1/2" in out
        assert "Batch 2/2" in out


# ---------------------------------------------------------------------------
# set_field (mocked)
# ---------------------------------------------------------------------------


class TestSetField:
    @patch.object(sp, "run")
    def test_single_select(self, mock_run):
        field_map = {
            "Status": {"id": "F1", "options": {"Done": "OPT1"}},
        }
        sp.set_field("PID", "ITEM", field_map, "Status", "Done")
        call_args = mock_run.call_args[0][0]
        assert "--single-select-option-id" in call_args
        assert "OPT1" in call_args

    @patch.object(sp, "run")
    def test_number(self, mock_run):
        field_map = {"Points": {"id": "F2"}}
        sp.set_field("PID", "ITEM", field_map, "Points", 5)
        call_args = mock_run.call_args[0][0]
        assert "--number" in call_args

    @patch.object(sp, "run")
    def test_date(self, mock_run):
        field_map = {"Start date": {"id": "F3"}}
        sp.set_field("PID", "ITEM", field_map, "Start date", "2026-01-01")
        call_args = mock_run.call_args[0][0]
        assert "--date" in call_args

    def test_none_value(self):
        sp.set_field("PID", "ITEM", {}, "Status", None)  # should not raise

    def test_empty_value(self):
        sp.set_field("PID", "ITEM", {}, "Status", "")  # should not raise

    def test_field_not_found(self, capsys):
        sp.set_field("PID", "ITEM", {}, "Missing", "val")
        assert "not found" in capsys.readouterr().err

    def test_invalid_option(self, capsys):
        field_map = {"Status": {"id": "F1", "options": {"Done": "OPT1"}}}
        sp.set_field("PID", "ITEM", field_map, "Status", "Invalid")
        assert "not found" in capsys.readouterr().err
