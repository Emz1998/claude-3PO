"""Tests for validate_sprint_md.py"""

import pytest

from validate_sprint_md import validate


VALID_SPRINT_MD = """\
# Sprint

**Sprint #:** 1
**Milestone:** v.0.1.0
**Goal:** Build foundational infrastructure
**Due Date:** 2026-03-02

---

## Sprint Overview

| ID     | Type  | Title          | Points | Status      | Blocked By |
| ------ | ----- | -------------- | ------ | ----------- | ---------- |
| US-001 | Story | Setup Firebase | 5      | In Progress | -          |

---

## Sprint Backlog

### User Stories

#### US-001: Setup Firebase

> **As a** developer, **I want** Firebase **so that** we have a backend.

**Labels:** setup, firebase
**Points:** 5
**Status:** In Progress
**TDD:** true
**Priority:** P0
**Is Blocking:** None
**Blocked By:** None
**Start Date:** 2026-02-17
**Target Date:** 2026-02-28

**Acceptance Criteria:**

- [ ] Firebase project created

**Tasks:**

- **T-001:** Create Firebase project
  - **Description:** Set up Firebase
  - **Status:** Done
  - **Priority:** P0
  - **Complexity:** S
  - **Labels:** setup
  - **Blocked by:** None
  - **Acceptance Criteria:**
    - [x] Project created
  - **Start date:** 2026-02-17
  - **Target date:** 2026-02-20
"""


# ── Valid Input ──────────────────────────────────────────────────────────────


class TestValidInput:
    def test_valid_sprint_has_no_errors(self):
        assert validate(VALID_SPRINT_MD) == []


# ── Metadata Validation ─────────────────────────────────────────────────────


class TestMetadataValidation:
    def test_missing_sprint_number(self):
        md = VALID_SPRINT_MD.replace("**Sprint #:** 1\n", "")
        errors = validate(md)
        assert any("Sprint #" in e for e in errors)

    def test_missing_milestone(self):
        md = VALID_SPRINT_MD.replace("**Milestone:** v.0.1.0\n", "")
        errors = validate(md)
        assert any("Milestone" in e for e in errors)

    def test_missing_goal(self):
        md = VALID_SPRINT_MD.replace("**Goal:** Build foundational infrastructure\n", "")
        errors = validate(md)
        assert any("Goal" in e for e in errors)

    def test_missing_due_date(self):
        md = VALID_SPRINT_MD.replace("**Due Date:** 2026-03-02\n", "")
        errors = validate(md)
        assert any("Due Date" in e for e in errors)

    def test_invalid_sprint_number(self):
        md = VALID_SPRINT_MD.replace("**Sprint #:** 1", "**Sprint #:** abc")
        errors = validate(md)
        assert any("must be a number" in e for e in errors)

    def test_invalid_due_date_format(self):
        md = VALID_SPRINT_MD.replace("**Due Date:** 2026-03-02", "**Due Date:** March 2")
        errors = validate(md)
        assert any("YYYY-MM-DD" in e for e in errors)

    def test_empty_goal(self):
        md = VALID_SPRINT_MD.replace("**Goal:** Build foundational infrastructure", "**Goal:**")
        errors = validate(md)
        assert any("empty" in e for e in errors)


# ── Table Validation ─────────────────────────────────────────────────────────


class TestTableValidation:
    def test_missing_table(self):
        md = "**Sprint #:** 1\n**Milestone:** v1\n**Goal:** test\n**Due Date:** 2026-01-01\n"
        errors = validate(md)
        assert any("table not found" in e for e in errors)

    def test_invalid_story_type_in_table(self):
        md = VALID_SPRINT_MD.replace("| US-001 | Story |", "| US-001 | Epic |")
        errors = validate(md)
        assert any("'Epic'" in e for e in errors)

    def test_mismatched_id_in_table(self):
        md = VALID_SPRINT_MD.replace("| US-001 | Story |", "| SK-001 | Story |")
        errors = validate(md)
        assert any("doesn't match pattern" in e for e in errors)

    def test_invalid_status_in_table(self):
        md = VALID_SPRINT_MD.replace("| In Progress |", "| Pending |")
        errors = validate(md)
        assert any("'Pending'" in e for e in errors)

    def test_invalid_points_in_table(self):
        md = VALID_SPRINT_MD.replace("| 5      | In Progress", "| abc    | In Progress")
        errors = validate(md)
        assert any("must be a number" in e for e in errors)


# ── Detail Section Validation ────────────────────────────────────────────────


class TestDetailSectionValidation:
    def test_missing_detail_section(self):
        md = VALID_SPRINT_MD.replace("#### US-001: Setup Firebase", "#### US-999: Other")
        errors = validate(md)
        assert any("missing detail section" in e for e in errors)

    def test_invalid_story_status(self):
        # Replace only the detail section status, not the table status
        md = VALID_SPRINT_MD.replace(
            "**Status:** In Progress\n**TDD:**",
            "**Status:** Pending\n**TDD:**",
        )
        errors = validate(md)
        assert any("'Pending'" in e for e in errors)

    def test_invalid_story_priority(self):
        md = VALID_SPRINT_MD.replace("**Priority:** P0\n**Is Blocking:**", "**Priority:** P9\n**Is Blocking:**")
        errors = validate(md)
        assert any("'P9'" in e for e in errors)

    def test_invalid_tdd_value(self):
        md = VALID_SPRINT_MD.replace("**TDD:** true", "**TDD:** maybe")
        errors = validate(md)
        assert any("'true' or 'false'" in e for e in errors)

    def test_missing_acceptance_criteria_section(self):
        md = VALID_SPRINT_MD.replace("**Acceptance Criteria:**", "**Notes:**")
        errors = validate(md)
        assert any("Acceptance Criteria" in e for e in errors)


# ── Task Section Validation ──────────────────────────────────────────────────


class TestTaskSectionValidation:
    def test_no_tasks_found(self):
        md = VALID_SPRINT_MD.replace("- **T-001:**", "- Some other content")
        errors = validate(md)
        assert any("no tasks found" in e for e in errors)

    def test_invalid_task_status(self):
        md = VALID_SPRINT_MD.replace(
            "**Status:** Done\n  - **Priority:** P0\n  - **Complexity:**",
            "**Status:** Waiting\n  - **Priority:** P0\n  - **Complexity:**",
        )
        errors = validate(md)
        assert any("'Waiting'" in e for e in errors)

    def test_invalid_task_priority(self):
        md = VALID_SPRINT_MD.replace(
            "- **Priority:** P0\n  - **Complexity:** S",
            "- **Priority:** P7\n  - **Complexity:** S",
        )
        errors = validate(md)
        assert any("'P7'" in e for e in errors)

    def test_invalid_task_complexity(self):
        md = VALID_SPRINT_MD.replace("**Complexity:** S", "**Complexity:** XL")
        errors = validate(md)
        assert any("'XL'" in e for e in errors)

    def test_missing_task_description(self):
        md = VALID_SPRINT_MD.replace("- **Description:** Set up Firebase\n", "")
        errors = validate(md)
        assert any("Description" in e for e in errors)

    def test_no_task_acceptance_criteria(self):
        md = VALID_SPRINT_MD.replace("    - [x] Project created\n", "")
        errors = validate(md)
        assert any("acceptance criteria" in e for e in errors)


# ── Multiple Stories ─────────────────────────────────────────────────────────


MULTI_STORY_MD = """\
# Sprint

**Sprint #:** 2
**Milestone:** v.0.2.0
**Goal:** Add features
**Due Date:** 2026-04-01

---

## Sprint Overview

| ID     | Type  | Title  | Points | Status | Blocked By |
| ------ | ----- | ------ | ------ | ------ | ---------- |
| US-001 | Story | Login  | 3      | Ready  | -          |
| BG-001 | Bug   | Fix UI | 1      | Ready  | -          |

---

## Sprint Backlog

### User Stories

#### US-001: Login

> **As a** user, **I want** to log in.

**Labels:** auth
**Points:** 3
**Status:** Ready
**TDD:** false
**Priority:** P1
**Is Blocking:** None
**Blocked By:** None
**Start Date:** 2026-03-01
**Target Date:** 2026-03-15

**Acceptance Criteria:**

- [ ] Can log in

**Tasks:**

- **T-001:** Build login
  - **Description:** Create login page
  - **Status:** Backlog
  - **Priority:** P1
  - **Complexity:** M
  - **Labels:** frontend
  - **Blocked by:** None
  - **Acceptance Criteria:**
    - [ ] Login page renders
  - **Start date:** 2026-03-01
  - **Target date:** 2026-03-10

### Bugs

#### BG-001: Fix UI

> **What's broken:** Button misaligned

**Labels:** bugfix
**Points:** 1
**Status:** Ready
**TDD:** true
**Priority:** P0
**Is Blocking:** None
**Blocked By:** None
**Start Date:** 2026-03-01
**Target Date:** 2026-03-15

**Acceptance Criteria:**

- [ ] Button aligned

**Tasks:**

- **T-002:** Fix button CSS
  - **Description:** Align the button
  - **Status:** Backlog
  - **Priority:** P0
  - **Complexity:** S
  - **Labels:** bugfix, frontend
  - **Blocked by:** None
  - **Acceptance Criteria:**
    - [ ] Button is centered
  - **Start date:** 2026-03-01
  - **Target date:** 2026-03-10
"""


class TestMultipleStories:
    def test_multiple_stories_valid(self):
        assert validate(MULTI_STORY_MD) == []
