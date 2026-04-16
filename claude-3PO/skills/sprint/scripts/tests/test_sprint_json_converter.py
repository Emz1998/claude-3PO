"""Tests for sprint_json_converter.py"""

import json
from pathlib import Path

import pytest

from sprint_json_converter import (
    _safe_int,
    _story_type,
    _parse_csv,
    _parse_field,
    _parse_header_line,
    _parse_due_date,
    _parse_sprint_metadata,
    _parse_story_description,
    _parse_story_fields,
    _parse_story_acceptance_criteria,
    _parse_task_title,
    _parse_task_blocked_by,
    _parse_task_fields,
    _parse_single_task,
    _parse_tasks,
    _build_spike_task,
    _parse_spike_as_tasks,
    _compute_is_blocking,
    convert,
)

SAMPLE_JSON = Path(__file__).resolve().parent.parent.parent / "sample_structure.json"


# ── Utilities ────────────────────────────────────────────────────────────────


class TestSafeInt:
    def test_valid_int(self):
        assert _safe_int("42") == 42

    def test_zero(self):
        assert _safe_int("0") == 0

    def test_invalid_returns_default(self):
        assert _safe_int("abc") == 0

    def test_custom_default(self):
        assert _safe_int("abc", default=-1) == -1

    def test_empty_string(self):
        assert _safe_int("") == 0


class TestStoryType:
    @pytest.mark.parametrize("prefix,expected", [
        ("US", "User Story"),
        ("TS", "Technical Story"),
        ("BG", "Bug"),
        ("SK", "Spike"),
    ])
    def test_known_prefixes(self, prefix, expected):
        assert _story_type(prefix) == expected

    def test_unknown_prefix_defaults_to_user_story(self):
        assert _story_type("XX") == "User Story"


class TestParseCsv:
    def test_comma_separated(self):
        assert _parse_csv("setup, firebase, backend") == ["setup", "firebase", "backend"]

    def test_single_value(self):
        assert _parse_csv("backend") == ["backend"]

    def test_skip_dash(self):
        assert _parse_csv("-") == []

    def test_skip_none(self):
        assert _parse_csv("None") == []

    def test_skip_empty(self):
        assert _parse_csv("") == []

    def test_strips_whitespace(self):
        assert _parse_csv("  a , b , c  ") == ["a", "b", "c"]


class TestParseField:
    def test_extracts_value(self):
        block = "**Status:** In Progress\n**Priority:** P0"
        assert _parse_field(block, "Status") == "In Progress"
        assert _parse_field(block, "Priority") == "P0"

    def test_missing_field(self):
        assert _parse_field("some text", "Status") == ""

    def test_label_with_special_chars(self):
        block = "**Is Blocking:** TS-002"
        assert _parse_field(block, "Is Blocking") == "TS-002"


# ── Sprint Metadata ─────────────────────────────────────────────────────────


class TestParseHeaderLine:
    def test_extracts_after_prefix(self):
        assert _parse_header_line("**Sprint #:** 1", "**Sprint #:**") == "1"

    def test_strips_whitespace(self):
        assert _parse_header_line("**Goal:**   Build stuff  ", "**Goal:**") == "Build stuff"


class TestParseDueDate:
    def test_arrow_separator(self):
        assert _parse_due_date("**Dates:** 2026-02-17 → 2026-03-02") == "2026-03-02"

    def test_dash_arrow_separator(self):
        assert _parse_due_date("**Dates:** 2026-02-17 -> 2026-03-02") == "2026-03-02"

    def test_to_separator(self):
        assert _parse_due_date("**Dates:** 2026-02-17 to 2026-03-02") == "2026-03-02"

    def test_single_date(self):
        assert _parse_due_date("**Dates:** 2026-03-02") == "2026-03-02"


class TestParseSprintMetadata:
    def test_all_fields(self):
        content = (
            "**Sprint #:** 1\n"
            "**Milestone:** v.0.1.0\n"
            "**Goal:** Build the thing\n"
            "**Due Date:** 2026-03-02\n"
        )
        result = _parse_sprint_metadata(content)
        assert result == {
            "sprint": 1,
            "milestone": "v.0.1.0",
            "description": "Build the thing",
            "due_date": "2026-03-02",
        }

    def test_dates_field_fallback(self):
        content = (
            "**Sprint #:** 2\n"
            "**Milestone:** v.0.2.0\n"
            "**Goal:** Ship it\n"
            "**Dates:** 2026-02-17 → 2026-03-02\n"
        )
        result = _parse_sprint_metadata(content)
        assert result["due_date"] == "2026-03-02"

    def test_missing_fields_get_defaults(self):
        result = _parse_sprint_metadata("")
        assert result == {"sprint": 0, "milestone": "", "description": "", "due_date": ""}


# ── Story Parsing ────────────────────────────────────────────────────────────


STORY_BLOCK = """\
> **As a** user, **I want** login **so that** I can access the app.

**Labels:** setup, backend
**Points:** 5
**Status:** In Progress
**TDD:** true
**Priority:** P0
**Is Blocking:** TS-002
**Blocked By:** None
**Start Date:** 2026-02-17
**Target Date:** 2026-02-28

**Acceptance Criteria:**

- [ ] User can log in
- [x] Session persists

**Tasks:**

- **T-001:** Create login endpoint
  - **Description:** Build the POST /login route
  - **Status:** Done
  - **Priority:** P0
  - **Complexity:** S
  - **Labels:** backend, auth
  - **Blocked by:** None
  - **Acceptance Criteria:**
    - [x] Endpoint returns 200
  - **Start date:** 2026-02-17
  - **Target date:** 2026-02-20

- **T-002:** Add session middleware
  - **Description:** Wire up session store
  - **Status:** In Progress
  - **Priority:** P1
  - **Complexity:** M
  - **Labels:** backend
  - **Blocked by:** T-001
  - **Acceptance Criteria:**
    - [ ] Sessions persist across requests
  - **Start date:**
  - **Target date:**
"""


class TestParseStoryDescription:
    def test_single_line_blockquote(self):
        block = "> Some description here\n\n**Status:** Ready"
        assert _parse_story_description(block) == "Some description here"

    def test_multiline_blockquote(self):
        block = "> Line one\n> Line two\n\n**Status:** Ready"
        result = _parse_story_description(block)
        assert "Line one" in result
        assert "Line two" in result

    def test_no_blockquote(self):
        assert _parse_story_description("**Status:** Ready") == ""


class TestParseStoryFields:
    def test_extracts_all_fields(self):
        fields = _parse_story_fields(STORY_BLOCK)
        assert fields["status"] == "In Progress"
        assert fields["priority"] == "P0"
        assert fields["labels"] == ["setup", "backend"]
        assert fields["points"] == 5
        assert fields["tdd"] is True
        assert fields["is_blocking"] == ["TS-002"]
        assert fields["blocked_by"] == []
        assert fields["start_date"] == "2026-02-17"
        assert fields["target_date"] == "2026-02-28"

    def test_defaults_status_to_ready(self):
        fields = _parse_story_fields("**Priority:** P1")
        assert fields["status"] == "Ready"

    def test_tdd_false(self):
        fields = _parse_story_fields("**TDD:** false")
        assert fields["tdd"] is False


class TestParseStoryAcceptanceCriteria:
    def test_extracts_before_tasks(self):
        ac = _parse_story_acceptance_criteria(STORY_BLOCK)
        assert ac == ["User can log in", "Session persists"]

    def test_no_tasks_section(self):
        block = "- [ ] First\n- [x] Second"
        assert _parse_story_acceptance_criteria(block) == ["First", "Second"]

    def test_no_criteria(self):
        assert _parse_story_acceptance_criteria("no checklist here") == []


# ── Task Parsing ─────────────────────────────────────────────────────────────


TASK_BODY = """\
 Create login endpoint
  - **Description:** Build the POST /login route
  - **Status:** Done
  - **Priority:** P0
  - **Complexity:** S
  - **Labels:** backend, auth
  - **Blocked by:** T-003
  - **Acceptance Criteria:**
    - [x] Endpoint returns 200
    - [ ] Returns JWT token
  - **Start date:** 2026-02-17
  - **Target date:** 2026-02-20
"""


class TestParseTaskTitle:
    def test_extracts_title(self):
        assert _parse_task_title(TASK_BODY) == "Create login endpoint"

    def test_empty_body(self):
        assert _parse_task_title("") == ""


class TestParseTaskBlockedBy:
    def test_blocked_by_field(self):
        assert _parse_task_blocked_by(TASK_BODY) == ["T-003"]

    def test_depends_on_fallback(self):
        body = "**Depends on:** T-010, T-011"
        assert _parse_task_blocked_by(body) == ["T-010", "T-011"]

    def test_none_value(self):
        body = "**Blocked by:** None"
        assert _parse_task_blocked_by(body) == []

    def test_no_field(self):
        assert _parse_task_blocked_by("no fields here") == []


class TestParseTaskFields:
    def test_extracts_all_fields(self):
        fields = _parse_task_fields(TASK_BODY)
        assert fields["description"] == "Build the POST /login route"
        assert fields["status"] == "Done"
        assert fields["priority"] == "P0"
        assert fields["complexity"] == "S"
        assert fields["labels"] == ["backend", "auth"]
        assert fields["acceptance_criteria"] == ["Endpoint returns 200", "Returns JWT token"]
        assert fields["start_date"] == "2026-02-17"
        assert fields["target_date"] == "2026-02-20"

    def test_defaults_status_to_backlog(self):
        fields = _parse_task_fields("**Priority:** P1")
        assert fields["status"] == "Backlog"


class TestParseSingleTask:
    def test_builds_task_dict(self):
        task = _parse_single_task("T-001", TASK_BODY, "v.0.1.0")
        assert task["id"] == "T-001"
        assert task["type"] == "task"
        assert task["item_type"] == "task"
        assert task["milestone"] == "v.0.1.0"
        assert task["title"] == "Create login endpoint"
        assert task["is_blocking"] == []
        assert task["blocked_by"] == ["T-003"]
        assert task["status"] == "Done"


class TestParseTasks:
    def test_parses_multiple_tasks(self):
        tasks = _parse_tasks(STORY_BLOCK, "v.0.1.0")
        assert len(tasks) == 2
        assert tasks[0]["id"] == "T-001"
        assert tasks[0]["title"] == "Create login endpoint"
        assert tasks[1]["id"] == "T-002"
        assert tasks[1]["title"] == "Add session middleware"

    def test_no_tasks(self):
        assert _parse_tasks("no tasks here", "v.0.1.0") == []


# ── Spike Tasks ──────────────────────────────────────────────────────────────


class TestBuildSpikeTask:
    def test_builds_correct_structure(self):
        task = _build_spike_task("T-00101", "Analyze data", "v.0.1.0")
        assert task["id"] == "T-00101"
        assert task["title"] == "Analyze data"
        assert task["labels"] == ["analysis", "documentation"]
        assert task["status"] == "Backlog"
        assert task["priority"] == "P1"
        assert task["complexity"] == "M"
        assert task["acceptance_criteria"] == ["Analyze data"]
        assert task["milestone"] == "v.0.1.0"


class TestParseSpikeAsTasks:
    def test_creates_tasks_from_deliverables(self):
        block = "- [ ] Research options\n- [x] Write report"
        tasks = _parse_spike_as_tasks(block, "SK-001", "v.0.1.0")
        assert len(tasks) == 2
        assert tasks[0]["id"] == "T-00101"
        assert tasks[0]["title"] == "Research options"
        assert tasks[1]["id"] == "T-00102"
        assert tasks[1]["title"] == "Write report"

    def test_no_deliverables(self):
        assert _parse_spike_as_tasks("no items", "SK-001", "v.0.1.0") == []


# ── Compute Is Blocking ─────────────────────────────────────────────────────


class TestComputeIsBlocking:
    def test_inverts_blocked_by(self):
        tasks = [
            {"id": "T-001", "blocked_by": [], "is_blocking": []},
            {"id": "T-002", "blocked_by": ["T-001"], "is_blocking": []},
        ]
        _compute_is_blocking(tasks)
        assert tasks[0]["is_blocking"] == ["T-002"]
        assert tasks[1]["is_blocking"] == []

    def test_chain_dependency(self):
        tasks = [
            {"id": "T-001", "blocked_by": [], "is_blocking": []},
            {"id": "T-002", "blocked_by": ["T-001"], "is_blocking": []},
            {"id": "T-003", "blocked_by": ["T-002"], "is_blocking": []},
        ]
        _compute_is_blocking(tasks)
        assert tasks[0]["is_blocking"] == ["T-002"]
        assert tasks[1]["is_blocking"] == ["T-003"]
        assert tasks[2]["is_blocking"] == []

    def test_ignores_unknown_ids(self):
        tasks = [
            {"id": "T-001", "blocked_by": ["T-999"], "is_blocking": []},
        ]
        _compute_is_blocking(tasks)
        assert tasks[0]["is_blocking"] == []

    def test_no_duplicates(self):
        tasks = [
            {"id": "T-001", "blocked_by": [], "is_blocking": ["T-002"]},
            {"id": "T-002", "blocked_by": ["T-001"], "is_blocking": []},
        ]
        _compute_is_blocking(tasks)
        assert tasks[0]["is_blocking"] == ["T-002"]


# ── End-to-End Convert ───────────────────────────────────────────────────────


SPRINT_MD = """\
**Sprint #:** 1
**Milestone:** v.0.1.0
**Goal:** Establish foundational infrastructure
**Due Date:** 2026-03-02

---

## Sprint Backlog

### User Stories

#### US-001: Setup Firebase

> **As a** developer, **I want** Firebase configured **so that** we have a backend.

**Labels:** setup, firebase
**Points:** 3
**Status:** In Progress
**TDD:** true
**Priority:** P0
**Is Blocking:** None
**Blocked By:** None
**Start Date:** 2026-02-17
**Target Date:** 2026-02-28

**Acceptance Criteria:**

- [ ] Firebase project created
- [ ] Firestore initialized

**Tasks:**

- **T-001:** Create Firebase project
  - **Description:** Set up Firebase project
  - **Status:** Done
  - **Priority:** P0
  - **Complexity:** S
  - **Labels:** setup, firebase
  - **Blocked by:** None
  - **Acceptance Criteria:**
    - [x] Firebase project created
  - **Start date:** 2026-02-17
  - **Target date:** 2026-02-20

- **T-002:** Initialize Firestore
  - **Description:** Create collections
  - **Status:** In Progress
  - **Priority:** P0
  - **Complexity:** M
  - **Labels:** database, firestore
  - **Blocked by:** T-001
  - **Acceptance Criteria:**
    - [ ] Collections created
  - **Start date:**
  - **Target date:**
"""


class TestConvert:
    def test_full_conversion(self):
        result = convert(SPRINT_MD)
        assert result["sprint"] == 1
        assert result["milestone"] == "v.0.1.0"
        assert result["description"] == "Establish foundational infrastructure"
        assert result["due_date"] == "2026-03-02"
        assert len(result["stories"]) == 1

        story = result["stories"][0]
        assert story["id"] == "US-001"
        assert story["type"] == "User Story"
        assert story["title"] == "Setup Firebase"
        assert story["status"] == "In Progress"
        assert story["tdd"] is True
        assert story["points"] == 3
        assert len(story["acceptance_criteria"]) == 2
        assert len(story["tasks"]) == 2

        t1, t2 = story["tasks"]
        assert t1["id"] == "T-001"
        assert t1["status"] == "Done"
        assert t1["is_blocking"] == ["T-002"]
        assert t2["id"] == "T-002"
        assert t2["blocked_by"] == ["T-001"]

    def test_matches_sample_structure_schema(self):
        """Verify output has the same top-level keys as sample_structure.json."""
        sample = json.loads(SAMPLE_JSON.read_text())
        result = convert(SPRINT_MD)

        assert set(result.keys()) == set(sample.keys())

        sample_story_keys = set(sample["stories"][0].keys())
        result_story_keys = set(result["stories"][0].keys())
        assert result_story_keys == sample_story_keys

        sample_task_keys = set(sample["stories"][0]["tasks"][0].keys())
        result_task_keys = set(result["stories"][0]["tasks"][0].keys())
        assert result_task_keys == sample_task_keys
