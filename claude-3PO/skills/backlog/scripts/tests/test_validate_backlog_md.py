"""Tests for validate_backlog_md.py"""

import pytest

from validate_backlog_md import validate


VALID_BACKLOG_MD = """\
# Backlog

**Project:** `TestProject`
**Last Updated:** `2026-04-15`

---

## Priority Legend

| Symbol | Meaning |
| ------ | ------- |
| P0     | Critical|

## ID Conventions

| Prefix | Type          |
| ------ | ------------- |
| US     | User Story    |

## Stories

### US-001: Setup Firebase

> **As a** developer, **I want** Firebase configured **so that** we have a backend.

**Description:** Configure Firebase project
**Priority:** P0
**Milestone:** v.0.1.0
**Is Blocking:** None
**Blocked By:** None

- [ ] Firebase project created
- [ ] Firestore initialized
"""


# ── Valid Input ──────────────────────────────────────────────────────────────


class TestValidInput:
    def test_valid_backlog_has_no_errors(self):
        assert validate(VALID_BACKLOG_MD) == []


# ── Metadata Validation ─────────────────────────────────────────────────────


class TestMetadataValidation:
    def test_missing_project(self):
        md = VALID_BACKLOG_MD.replace("**Project:** `TestProject`\n", "")
        errors = validate(md)
        assert any("Project" in e for e in errors)

    def test_missing_last_updated(self):
        md = VALID_BACKLOG_MD.replace("**Last Updated:** `2026-04-15`\n", "")
        errors = validate(md)
        assert any("Last Updated" in e for e in errors)

    def test_empty_project(self):
        md = VALID_BACKLOG_MD.replace("**Project:** `TestProject`", "**Project:**")
        errors = validate(md)
        assert any("empty" in e or "placeholder" in e for e in errors)


# ── Section Validation ──────────────────────────────────────────────────────


class TestSectionValidation:
    def test_unknown_section(self):
        md = VALID_BACKLOG_MD + "\n## Unknown Section\n"
        errors = validate(md)
        assert any("Unknown Section" in e or "unknown section" in e for e in errors)

    def test_valid_sections_pass(self):
        errors = validate(VALID_BACKLOG_MD)
        section_errors = [e for e in errors if "section" in e.lower()]
        assert section_errors == []


# ── Story Validation ────────────────────────────────────────────────────────


class TestStoryValidation:
    def test_no_stories_found(self):
        md = "**Project:** `Test`\n**Last Updated:** `2026-01-01`\n\n## Stories\n"
        errors = validate(md)
        assert any("no story" in e for e in errors)

    def test_invalid_id_prefix(self):
        md = VALID_BACKLOG_MD.replace("### US-001:", "### XX-001:")
        errors = validate(md)
        assert any("prefix" in e.lower() or "XX" in e for e in errors)

    def test_empty_title(self):
        md = VALID_BACKLOG_MD.replace("### US-001: Setup Firebase", "### US-001: ")
        errors = validate(md)
        assert any("title" in e.lower() for e in errors)

    def test_empty_description(self):
        md = VALID_BACKLOG_MD.replace(
            "**Description:** Configure Firebase project",
            "**Description:**",
        )
        errors = validate(md)
        assert any("description" in e.lower() for e in errors)

    def test_missing_priority(self):
        md = VALID_BACKLOG_MD.replace("**Priority:** P0\n", "")
        errors = validate(md)
        assert any("Priority" in e or "priority" in e for e in errors)

    def test_invalid_priority(self):
        md = VALID_BACKLOG_MD.replace("**Priority:** P0", "**Priority:** P9")
        errors = validate(md)
        assert any("P9" in e for e in errors)

    def test_missing_acceptance_criteria(self):
        md = VALID_BACKLOG_MD.replace("- [ ] Firebase project created\n- [ ] Firestore initialized\n", "")
        errors = validate(md)
        assert any("criteria" in e.lower() or "acceptance" in e.lower() for e in errors)


# ── Story Format Validation ──────────────────────────────────────────────────


class TestStoryFormatValidation:
    def test_us_missing_as_a(self):
        md = VALID_BACKLOG_MD.replace(
            '> **As a** developer, **I want** Firebase configured **so that** we have a backend.',
            '> Some other format',
        )
        errors = validate(md)
        assert any("As a" in e for e in errors)

    def test_ts_missing_as_a(self):
        md = VALID_BACKLOG_MD.replace("### US-001:", "### TS-001:")
        md = md.replace(
            '> **As a** developer, **I want** Firebase configured **so that** we have a backend.',
            '> Some other format',
        )
        errors = validate(md)
        assert any("As a" in e for e in errors)

    def test_sk_missing_investigate(self):
        md = VALID_BACKLOG_MD.replace("### US-001:", "### SK-001:")
        md = md.replace(
            '> **As a** developer, **I want** Firebase configured **so that** we have a backend.',
            '> Some other format',
        )
        errors = validate(md)
        assert any("Investigate" in e for e in errors)

    def test_bg_missing_whats_broken(self):
        md = VALID_BACKLOG_MD.replace("### US-001:", "### BG-001:")
        md = md.replace(
            '> **As a** developer, **I want** Firebase configured **so that** we have a backend.',
            '> Some other format',
        )
        errors = validate(md)
        assert any("broken" in e.lower() for e in errors)


# ── Multiple Stories ─────────────────────────────────────────────────────────


MULTI_STORY_MD = """\
# Backlog

**Project:** `TestProject`
**Last Updated:** `2026-04-15`

## Stories

### US-001: Login

> **As a** user, **I want** to log in **so that** I access the app.

**Description:** Build login
**Priority:** P0
**Milestone:** v.0.1.0
**Is Blocking:** None
**Blocked By:** None

- [ ] Can log in

### BG-001: Fix crash

> **What's broken:** App crashes on load

**Description:** Fix startup crash
**Priority:** P1
**Milestone:** v.0.1.0
**Is Blocking:** None
**Blocked By:** None

- [ ] App starts without crash
"""


class TestMultipleStories:
    def test_multiple_stories_valid(self):
        assert validate(MULTI_STORY_MD) == []

    def test_both_stories_parsed(self):
        errors = validate(MULTI_STORY_MD)
        assert errors == []
