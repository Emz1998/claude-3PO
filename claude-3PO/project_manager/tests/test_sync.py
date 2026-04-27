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
                    "labels": ["analysis"],
                    "title": "Analyze features",
                    "description": "Perform analysis",
                    "status": "In progress",
                    "priority": "P1",
                    "complexity": "M",
                    "acceptance_criteria": ["Analysis done"],
                },
                {
                    "id": "T-002",
                    "type": "task",
                    "labels": ["docs"],
                    "title": "Document findings",
                    "description": "Write docs",
                    "status": "Ready",
                    "priority": "P2",
                    "complexity": "S",
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
                    "labels": ["infra"],
                    "title": "Create repo",
                    "description": "Create the repository",
                    "status": "Done",
                    "priority": "P0",
                    "complexity": "S",
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
    def test_writes_story_issue_numbers_only(self, tmp_path):
        p = tmp_path / "b.json"
        backlog = {
            "stories": [
                {"id": "SK-001", "tasks": [{"id": "T-001"}]},
            ],
        }
        p.write_text(json.dumps(backlog), encoding="utf-8")
        _, _, _, backlog_data = sp.load_flat_data(p)
        # Simulate sync assigning a story issue number; tasks are decoupled
        # from GitHub now and never get one.
        backlog_data["stories"][0]["issue_number"] = 999
        sp.save_flat_data(
            [backlog_data["stories"][0]], [], p, backlog_data,
        )
        reloaded = json.loads(p.read_text(encoding="utf-8"))
        assert reloaded["stories"][0]["issue_number"] == 999
        assert "issue_number" not in reloaded["stories"][0]["tasks"][0]

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
    @patch.object(sp, "_fetch_node_ids_and_edges",
                  return_value=({100: "NODE-100", 200: "NODE-200"}, set(), {}))
    @patch.object(sp, "execute_batched_mutations")
    def test_calls_addBlockedBy(self, mock_exec, mock_fetch):
        items = [{"id": "T-001", "issue_number": 100, "blocked_by": ["SK-001"]}]
        id_map = {"SK-001": 200}
        sp.set_blocking_relationships("org/repo", items, id_map)
        mutations = mock_exec.call_args[0][0]
        assert any("addBlockedBy" in m for m in mutations)
        assert len(mutations) == 1

    @patch.object(sp, "_fetch_node_ids_and_edges", return_value=({}, set(), {}))
    @patch.object(sp, "execute_batched_mutations")
    def test_skips_empty(self, mock_exec, mock_fetch, capsys):
        sp.set_blocking_relationships("org/repo", [], {})
        assert "No blocking" in capsys.readouterr().out
        mock_exec.assert_not_called()

    @patch.object(sp, "_fetch_node_ids_and_edges", return_value=({}, set(), {}))
    @patch.object(sp, "execute_batched_mutations")
    def test_skips_when_node_id_missing(self, mock_exec, mock_fetch, capsys):
        items = [{"id": "T-001", "issue_number": 100, "blocked_by": ["SK-001"]}]
        sp.set_blocking_relationships("org/repo", items, {"SK-001": 200})
        out = capsys.readouterr().out
        assert "Missing node ID" in out
        # Called but with zero mutations (all pairs skipped)
        mutations = mock_exec.call_args[0][0]
        assert mutations == []

    @patch.object(sp, "_fetch_node_ids_and_edges",
                  return_value=({100: "NODE-100"}, set(), {}))
    @patch.object(sp, "execute_batched_mutations")
    def test_skips_unresolved_ids(self, mock_exec, mock_fetch):
        items = [{"id": "T-001", "issue_number": 100, "blocked_by": ["MISSING"]}]
        sp.set_blocking_relationships("org/repo", items, {})
        # No pairs collected → no mutations produced → exec not called
        mock_exec.assert_not_called()

    @patch.object(sp, "_fetch_node_ids_and_edges",
                  return_value=({100: "NODE-100", 200: "NODE-200"}, set(), {}))
    @patch.object(sp, "execute_batched_mutations")
    def test_reuses_node_ids_when_provided(self, mock_exec, mock_fetch):
        items = [{"id": "T-001", "issue_number": 100, "blocked_by": ["SK-001"]}]
        id_map = {"SK-001": 200}
        node_ids = {100: "NODE-100", 200: "NODE-200"}
        sp.set_blocking_relationships(
            "org/repo", items, id_map, node_ids=node_ids, existing_edges=set()
        )
        mutations = mock_exec.call_args[0][0]
        assert any("addBlockedBy" in m for m in mutations)

    @patch.object(sp, "_fetch_node_ids_and_edges",
                  return_value=({100: "NODE-100", 200: "NODE-200"}, {(100, 200)}, {}))
    @patch.object(sp, "execute_batched_mutations")
    def test_skips_pairs_already_set_on_github(self, mock_exec, mock_fetch):
        # The (blocked=100, blocker=200) edge already exists remotely.
        # Pass 4 must not re-assert it — GitHub rejects the whole batch
        # with "Target issue has already been taken" when it does.
        items = [{"id": "T-001", "issue_number": 100, "blocked_by": ["SK-001"]}]
        id_map = {"SK-001": 200}
        sp.set_blocking_relationships("org/repo", items, id_map)
        mutations = mock_exec.call_args[0][0]
        assert mutations == []

    @patch.object(sp, "_fetch_node_ids_and_edges",
                  return_value=({100: "NODE-100", 200: "NODE-200", 300: "NODE-300"},
                                {(100, 200)}, {}))
    @patch.object(sp, "execute_batched_mutations")
    def test_sends_only_new_edges(self, mock_exec, mock_fetch):
        # One edge exists (100→200), another is new (100→300).
        items = [{
            "id": "T-001", "issue_number": 100,
            "blocked_by": ["SK-001", "SK-002"],
        }]
        id_map = {"SK-001": 200, "SK-002": 300}
        sp.set_blocking_relationships("org/repo", items, id_map)
        mutations = mock_exec.call_args[0][0]
        assert len(mutations) == 1
        # The remaining mutation is for the *new* blocker (NODE-300).
        assert "NODE-300" in mutations[0]


class TestFetchNodeIdsAndEdges:
    @patch.object(sp, "gh_json")
    def test_parses_ids_edges_and_parents(self, mock_gh):
        # Simulate the GraphQL shape: each issue alias returns id, number,
        # `blockedBy`, and `parent`. The helper must collapse that into
        # (num->node_id, {(blocked_num, blocker_num)}, {child_num: parent_num}).
        mock_gh.return_value = {
            "data": {"repository": {
                "i100": {"id": "NODE-100", "number": 100,
                         "blockedBy": {"nodes": [{"number": 200}]},
                         "parent": {"number": 300}},
                "i200": {"id": "NODE-200", "number": 200,
                         "blockedBy": {"nodes": []}, "parent": None},
            }}
        }
        ids, edges, parents = sp._fetch_node_ids_and_edges("org/repo", {100, 200})
        assert ids == {100: "NODE-100", 200: "NODE-200"}
        assert edges == {(100, 200)}
        assert parents == {100: 300}

    @patch.object(sp, "gh_json")
    def test_empty_input_skips_query(self, mock_gh):
        ids, edges, parents = sp._fetch_node_ids_and_edges("org/repo", set())
        assert ids == {} and edges == set() and parents == {}
        mock_gh.assert_not_called()

    def test_query_uses_blockedBy_field(self):
        # Regression guard: GitHub renamed `blockedByIssues` → `blockedBy`
        # on the Issue type. The old name triggers a hard query failure
        # ("Field 'blockedByIssues' doesn't exist on type 'Issue'") that
        # takes down every sync before Pass 2 even runs.
        query = sp._build_node_id_edges_query("org/repo", [100])
        assert "blockedBy(" in query
        assert "blockedByIssues" not in query


# ---------------------------------------------------------------------------
# resolve_existing_issues
# ---------------------------------------------------------------------------


class TestResolveExistingIssues:
    def test_live_issue_number_kept(self):
        tasks = [{"id": "T-001", "title": "X", "issue_number": 42}]
        # #42 is in the live cache → keep it, no re-creation
        assert sp.resolve_existing_issues(tasks, {"T-001: X": 42}) == []
        assert tasks[0]["issue_number"] == 42

    def test_stale_issue_number_dropped(self):
        tasks = [{"id": "T-001", "title": "X", "issue_number": 999}]
        # #999 not in live cache → dropped, treated as needs-creation
        needs = sp.resolve_existing_issues(tasks, {})
        assert needs == tasks
        assert "issue_number" not in tasks[0]

    def test_stale_number_relinks_by_title_if_possible(self):
        tasks = [{"id": "T-001", "title": "X", "issue_number": 999}]
        # Stale #999 dropped; title lookup finds live #42
        assert sp.resolve_existing_issues(tasks, {"T-001: X": 42}) == []
        assert tasks[0]["issue_number"] == 42

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
        # #1 is live (T-001 stays linked); T-003 matches by title; T-002 needs creation
        needs = sp.resolve_existing_issues(tasks, {"T-001: Has": 1, "T-003: Found": 5})
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
        mutations = sp._collect_mutations([story], items, "PID", field_map, {})
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
        mutations = sp._collect_mutations([task], items, "PID", field_map, {})
        flat = " ".join(mutations)
        assert "FC" in flat
        assert "FPts" not in flat

    def test_empty(self):
        assert sp._collect_mutations([], [], "PID", {}, {}) == []


# ---------------------------------------------------------------------------
# _extract_item_field_values + _build_remote_values_map
# ---------------------------------------------------------------------------


_PASS2_FIELD_MAP = {
    "Status": {"id": "FS", "options": {"In progress": "OS_IP", "Ready": "OS_R"}},
    "Priority": {"id": "FP", "options": {"P0": "OP0", "P1": "OP1"}},
    "Points": {"id": "FPts"},
    "Complexity": {"id": "FC", "options": {"M": "OM", "S": "OS_S"}},
    "Start date": {"id": "FSD"},
    "Target date": {"id": "FTD"},
}


class TestExtractItemFieldValues:
    def test_single_select_fields(self):
        raw = {
            "id": "PVT1", "status": "In progress", "priority": "P0",
            "complexity": "M",
        }
        result = sp._extract_item_field_values(raw)
        assert result["Status"] == "In progress"
        assert result["Priority"] == "P0"
        assert result["Complexity"] == "M"

    def test_number_field(self):
        result = sp._extract_item_field_values({"id": "X", "points": 3})
        assert result["Points"] == 3

    def test_date_fields(self):
        raw = {
            "id": "X", "start date": "2026-02-17", "target date": "2026-02-28",
        }
        result = sp._extract_item_field_values(raw)
        assert result["Start date"] == "2026-02-17"
        assert result["Target date"] == "2026-02-28"

    def test_iso_timestamp_date_normalized(self):
        raw = {"id": "X", "start date": "2026-02-17T00:00:00Z"}
        result = sp._extract_item_field_values(raw)
        assert result["Start date"] == "2026-02-17"

    def test_missing_fields_excluded(self):
        result = sp._extract_item_field_values({"id": "X", "status": "Ready"})
        assert "Status" in result
        assert "Priority" not in result
        assert "Points" not in result

    def test_empty(self):
        assert sp._extract_item_field_values({"id": "X"}) == {}


class TestBuildRemoteValuesMap:
    def test_builds_map(self):
        items = [
            {"id": "I1", "status": "In progress", "points": 5},
            {"id": "I2", "priority": "P0"},
        ]
        result = sp._build_remote_values_map(items)
        assert result["I1"] == {"Status": "In progress", "Points": 5}
        assert result["I2"] == {"Priority": "P0"}

    def test_skips_items_without_id(self):
        assert sp._build_remote_values_map([{"status": "Ready"}]) == {}


class TestBuildIssueMilestoneMap:
    def test_maps_milestones(self):
        issues = [
            {"number": 1, "title": "A", "milestone": {"title": "v0.1.0"}},
            {"number": 2, "title": "B", "milestone": {"title": "v0.2.0"}},
        ]
        assert sp.build_issue_milestone_map(issues) == {1: "v0.1.0", 2: "v0.2.0"}

    def test_none_milestone(self):
        issues = [{"number": 1, "title": "A", "milestone": None}]
        assert sp.build_issue_milestone_map(issues) == {1: ""}

    def test_missing_milestone(self):
        assert sp.build_issue_milestone_map([{"number": 1, "title": "A"}]) == {1: ""}


# ---------------------------------------------------------------------------
# Pass 2 diff: field updates skipped when remote already matches
# ---------------------------------------------------------------------------


class TestPass2Diffing:
    def _single_story_items(self):
        items = [{"id": "ITEM-1", "content": {"number": 1}}]
        return items

    def test_skips_field_when_value_unchanged(self):
        story = {
            "id": "SK-001", "item_type": "story", "issue_number": 1,
            "status": "In progress",
        }
        remote_by_item = {"ITEM-1": {"Status": "In progress"}}
        mutations = sp._collect_mutations(
            [story], self._single_story_items(), "PID", _PASS2_FIELD_MAP, remote_by_item,
        )
        assert mutations == []

    def test_emits_mutation_when_status_changes(self):
        story = {
            "id": "SK-001", "item_type": "story", "issue_number": 1,
            "status": "In progress",
        }
        remote_by_item = {"ITEM-1": {"Status": "Ready"}}
        mutations = sp._collect_mutations(
            [story], self._single_story_items(), "PID", _PASS2_FIELD_MAP, remote_by_item,
        )
        assert len(mutations) == 1
        assert "FS" in mutations[0]

    def test_normalizes_dates_before_comparing(self):
        story = {
            "id": "SK-001", "item_type": "story", "issue_number": 1,
            "start_date": "2026-02-17",
        }
        remote_by_item = {
            "ITEM-1": sp._extract_item_field_values(
                {"id": "ITEM-1", "start date": "2026-02-17T00:00:00Z"}
            ),
        }
        mutations = sp._collect_mutations(
            [story], self._single_story_items(), "PID", _PASS2_FIELD_MAP, remote_by_item,
        )
        assert mutations == []

    def test_story_vs_task_field_diff_independent(self):
        story = {
            "id": "SK-001", "item_type": "story", "issue_number": 1,
            "points": 5, "priority": "P0",
        }
        remote_by_item = {"ITEM-1": {"Priority": "P0", "Points": 3}}
        mutations = sp._collect_mutations(
            [story], self._single_story_items(), "PID", _PASS2_FIELD_MAP, remote_by_item,
        )
        assert len(mutations) == 1
        assert "FPts" in mutations[0]

    def test_all_fields_match_emits_zero_mutations(self):
        story = {
            "id": "SK-001", "item_type": "story", "issue_number": 1,
            "status": "In progress", "priority": "P0", "points": 3,
            "start_date": "2026-02-17", "target_date": "2026-02-28",
        }
        remote_by_item = {"ITEM-1": {
            "Status": "In progress", "Priority": "P0", "Points": 3,
            "Start date": "2026-02-17", "Target date": "2026-02-28",
        }}
        mutations = sp._collect_mutations(
            [story], self._single_story_items(), "PID", _PASS2_FIELD_MAP, remote_by_item,
        )
        assert mutations == []


# ---------------------------------------------------------------------------
# Issue-level edit: milestone diff
# ---------------------------------------------------------------------------


class TestIssueLevelDiff:
    @patch.object(sp, "create_branch_for_issue")
    @patch.object(sp, "set_parent_issue")
    @patch.object(sp, "run")
    def test_skips_gh_edit_when_milestone_matches(self, mock_run, *_):
        task = {"id": "T-001", "issue_number": 42, "milestone": "v0.1.0"}
        sp._issue_level_edit(task, "org/repo", remote_milestone="v0.1.0")
        edit_calls = [
            c for c in mock_run.call_args_list
            if "issue" in c[0][0] and "edit" in c[0][0]
        ]
        assert edit_calls == []

    @patch.object(sp, "create_branch_for_issue")
    @patch.object(sp, "set_parent_issue")
    @patch.object(sp, "run")
    def test_runs_gh_edit_when_milestone_differs(self, mock_run, *_):
        task = {"id": "T-001", "issue_number": 42, "milestone": "v0.2.0"}
        sp._issue_level_edit(task, "org/repo", remote_milestone="v0.1.0")
        cmds = [c[0][0] for c in mock_run.call_args_list]
        edit_cmd = next((c for c in cmds if "edit" in c), None)
        assert edit_cmd is not None
        assert "--milestone" in edit_cmd
        assert "v0.2.0" in edit_cmd

    @patch.object(sp, "create_branch_for_issue")
    @patch.object(sp, "set_parent_issue")
    @patch.object(sp, "run")
    def test_runs_gh_edit_when_remote_milestone_absent(self, mock_run, *_):
        task = {"id": "T-001", "issue_number": 42, "milestone": "v0.1.0"}
        sp._issue_level_edit(task, "org/repo", remote_milestone=None)
        cmds = [c[0][0] for c in mock_run.call_args_list]
        edit_cmd = next((c for c in cmds if "edit" in c), None)
        assert edit_cmd is not None
        assert "--milestone" in edit_cmd


# ---------------------------------------------------------------------------
# run_pass2_batched integration
# ---------------------------------------------------------------------------


class TestRunPass2Batched:
    _FIELD_MAP = _PASS2_FIELD_MAP

    def _matching_item(self, item_id: str, num: int) -> dict:
        return {
            "id": item_id, "content": {"number": num},
            "status": "In progress", "priority": "P0", "points": 3,
        }

    def _matching_story(self, sid: str, num: int) -> dict:
        return {
            "id": sid, "item_type": "story", "issue_number": num,
            "status": "In progress", "priority": "P0", "points": 3,
        }

    @patch.object(sp, "ensure_milestone")
    @patch.object(sp, "_apply_issue_level_parallel")
    @patch.object(sp, "execute_batched_mutations")
    def test_no_mutations_when_all_match(self, mock_exec, mock_parallel, _):
        items = [self._matching_item(f"ITEM-{i}", i) for i in range(21)]
        tasks = [self._matching_story(f"SK-{i:03d}", i) for i in range(21)]
        remote_by_item = sp._build_remote_values_map(items)
        sp.run_pass2_batched(
            tasks, items, "PID", self._FIELD_MAP, "org/repo",
            remote_by_item=remote_by_item, remote_milestones={},
        )
        assert mock_exec.call_args[0][0] == []

    @patch.object(sp, "ensure_milestone")
    @patch.object(sp, "_apply_issue_level_parallel")
    @patch.object(sp, "execute_batched_mutations")
    def test_exactly_one_mutation_when_single_status_differs(
        self, mock_exec, mock_parallel, _,
    ):
        items = [self._matching_item(f"ITEM-{i}", i) for i in range(21)]
        items[0]["status"] = "Ready"
        tasks = [self._matching_story(f"SK-{i:03d}", i) for i in range(21)]
        remote_by_item = sp._build_remote_values_map(items)
        sp.run_pass2_batched(
            tasks, items, "PID", self._FIELD_MAP, "org/repo",
            remote_by_item=remote_by_item, remote_milestones={},
        )
        mutations = mock_exec.call_args[0][0]
        assert len(mutations) == 1
        assert "FS" in mutations[0]


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

    def test_run_clears_created_titles(self, tmp_path):
        # The module-global _created_titles guards against creating two
        # issues with the same title in parallel *within one sync*. The
        # watcher keeps the process alive across many syncs, so the set
        # must be reset at the start of each run — otherwise a stale
        # title from a prior run trips the guard on the next run even
        # when there's no actual concurrency.
        sp._created_titles.add("SK-STALE: leftover from previous run")
        s = sp.Syncer(backlog_path=tmp_path / "b.json")
        with patch.object(s, "sync", return_value=0) as mock_sync:
            # Capture the state of the set *at the moment sync was called*.
            def record_and_return(**kwargs):
                captured["at_dispatch"] = set(sp._created_titles)
                return 0
            captured: dict = {}
            mock_sync.side_effect = record_and_return
            s.run("sync")
        assert captured["at_dispatch"] == set()


