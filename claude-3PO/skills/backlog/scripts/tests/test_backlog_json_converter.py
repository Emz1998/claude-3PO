"""Tests for backlog_json_converter.py"""

import json
from pathlib import Path

import pytest

from backlog_json_converter import (
    _story_type,
    _parse_list_field,
    _extract_metadata,
    _find_stories_section,
    _new_story,
    _parse_story_field,
    _parse_stories,
    convert,
)

SAMPLE_JSON = Path(__file__).resolve().parent.parent.parent / "sample_structure.json"


# ── Utilities ────────────────────────────────────────────────────────────────


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

    def test_empty_prefix(self):
        assert _story_type("") == "User Story"


class TestParseListField:
    def test_comma_separated(self):
        assert _parse_list_field("US-001, TS-002") == ["US-001", "TS-002"]

    def test_single_value(self):
        assert _parse_list_field("US-001") == ["US-001"]

    def test_none_string(self):
        assert _parse_list_field("None") == []

    def test_dash(self):
        assert _parse_list_field("-") == []

    def test_empty(self):
        assert _parse_list_field("") == []

    def test_placeholder_sk(self):
        assert _parse_list_field("None / SK-NNN") == []

    def test_placeholder_ts_us(self):
        assert _parse_list_field("None / TS-NNN, US-NNN") == []

    def test_strips_backticks(self):
        assert _parse_list_field("`US-001, TS-002`") == ["US-001", "TS-002"]

    def test_strips_brackets(self):
        assert _parse_list_field("[US-001, TS-002]") == ["US-001", "TS-002"]

    def test_strips_whitespace(self):
        assert _parse_list_field("  US-001 , TS-002  ") == ["US-001", "TS-002"]

    def test_filters_none_in_list(self):
        assert _parse_list_field("US-001, None") == ["US-001"]


# ── Metadata Extraction ─────────────────────────────────────────────────────


class TestExtractMetadata:
    def test_extracts_project_and_goal(self):
        lines = [
            "# Backlog",
            "**Project:** `MyProject`",
            "**Goal:** Build the thing",
        ]
        project, goal = _extract_metadata(lines)
        assert project == "MyProject"
        assert goal == "Build the thing"

    def test_missing_project(self):
        lines = ["**Goal:** Build the thing"]
        project, goal = _extract_metadata(lines)
        assert project == ""
        assert goal == "Build the thing"

    def test_missing_goal(self):
        lines = ["**Project:** `MyProject`"]
        project, goal = _extract_metadata(lines)
        assert project == "MyProject"
        assert goal == ""

    def test_empty_lines(self):
        project, goal = _extract_metadata([])
        assert project == ""
        assert goal == ""


# ── Find Stories Section ─────────────────────────────────────────────────────


class TestFindStoriesSection:
    def test_finds_section(self):
        lines = ["# Backlog", "", "## Stories", "### US-001: Title"]
        assert _find_stories_section(lines) == 2

    def test_returns_negative_when_missing(self):
        lines = ["# Backlog", "## Other"]
        assert _find_stories_section(lines) == -1

    def test_strips_whitespace(self):
        lines = ["  ## Stories  "]
        assert _find_stories_section(lines) == 0


# ── New Story ────────────────────────────────────────────────────────────────


class TestNewStory:
    def test_creates_user_story(self):
        story = _new_story("US-001", "Login feature")
        assert story["id"] == "US-001"
        assert story["type"] == "User Story"
        assert story["title"] == "Login feature"
        assert story["status"] == "Backlog"
        assert story["item_type"] == "story"

    def test_creates_spike(self):
        story = _new_story("SK-001", "Research options")
        assert story["type"] == "Spike"

    def test_creates_bug(self):
        story = _new_story("BG-001", "Fix crash")
        assert story["type"] == "Bug"

    def test_creates_technical_story(self):
        story = _new_story("TS-001", "Refactor auth")
        assert story["type"] == "Technical Story"

    def test_default_fields(self):
        story = _new_story("US-001", "Title")
        assert story["description"] == ""
        assert story["priority"] == ""
        assert story["is_blocking"] == []
        assert story["blocked_by"] == []
        assert story["acceptance_criteria"] == []
        assert story["milestone"] == ""
        assert story["start_date"] == ""
        assert story["target_date"] == ""

    def test_no_hyphen_in_id(self):
        story = _new_story("NOHYPHEN", "Title")
        assert story["type"] == "User Story"


# ── Parse Story Field ────────────────────────────────────────────────────────


class TestParseStoryField:
    def test_description(self):
        story = _new_story("US-001", "Title")
        _parse_story_field(story, "**Description:** `Build login page`")
        assert story["description"] == "Build login page"

    def test_priority(self):
        story = _new_story("US-001", "Title")
        _parse_story_field(story, "**Priority:** `P0`")
        assert story["priority"] == "P0"

    def test_milestone(self):
        story = _new_story("US-001", "Title")
        _parse_story_field(story, "**Milestone:** `v.0.1.0`")
        assert story["milestone"] == "v.0.1.0"

    def test_is_blocking(self):
        story = _new_story("US-001", "Title")
        _parse_story_field(story, "**Is Blocking:** TS-002, TS-003")
        assert story["is_blocking"] == ["TS-002", "TS-003"]

    def test_blocked_by(self):
        story = _new_story("US-001", "Title")
        _parse_story_field(story, "**Blocked By:** SK-001")
        assert story["blocked_by"] == ["SK-001"]

    def test_blocked_by_none(self):
        story = _new_story("US-001", "Title")
        _parse_story_field(story, "**Blocked By:** None")
        assert story["blocked_by"] == []

    def test_unchecked_acceptance_criterion(self):
        story = _new_story("US-001", "Title")
        _parse_story_field(story, "- [ ] User can log in")
        assert story["acceptance_criteria"] == ["User can log in"]

    def test_checked_acceptance_criterion(self):
        story = _new_story("US-001", "Title")
        _parse_story_field(story, "- [x] Session persists")
        assert story["acceptance_criteria"] == ["Session persists"]

    def test_multiple_criteria(self):
        story = _new_story("US-001", "Title")
        _parse_story_field(story, "- [ ] First")
        _parse_story_field(story, "- [x] Second")
        assert story["acceptance_criteria"] == ["First", "Second"]

    def test_unrecognized_line_is_ignored(self):
        story = _new_story("US-001", "Title")
        _parse_story_field(story, "Some random text")
        assert story["description"] == ""
        assert story["priority"] == ""


# ── Parse Stories ────────────────────────────────────────────────────────────


BACKLOG_STORIES_SECTION = """\
# Backlog

**Project:** `TestProject`
**Goal:** Test goal

## Stories

### US-001: Login feature
**Description:** Build login
**Priority:** P0
**Milestone:** v.0.1.0
**Is Blocking:** TS-002
**Blocked By:** None
- [ ] User can log in
- [x] Session persists

### TS-002: Auth middleware
**Description:** Setup auth layer
**Priority:** P1
**Milestone:** v.0.1.0
**Is Blocking:** None
**Blocked By:** US-001
- [ ] Middleware configured
"""


class TestParseStories:
    def test_parses_multiple_stories(self):
        lines = BACKLOG_STORIES_SECTION.split("\n")
        stories = _parse_stories(lines)
        assert len(stories) == 2

    def test_first_story_fields(self):
        lines = BACKLOG_STORIES_SECTION.split("\n")
        stories = _parse_stories(lines)
        s = stories[0]
        assert s["id"] == "US-001"
        assert s["type"] == "User Story"
        assert s["title"] == "Login feature"
        assert s["description"] == "Build login"
        assert s["priority"] == "P0"
        assert s["milestone"] == "v.0.1.0"
        assert s["is_blocking"] == ["TS-002"]
        assert s["blocked_by"] == []
        assert s["acceptance_criteria"] == ["User can log in", "Session persists"]

    def test_second_story_fields(self):
        lines = BACKLOG_STORIES_SECTION.split("\n")
        stories = _parse_stories(lines)
        s = stories[1]
        assert s["id"] == "TS-002"
        assert s["type"] == "Technical Story"
        assert s["title"] == "Auth middleware"
        assert s["blocked_by"] == ["US-001"]

    def test_no_stories_section(self):
        lines = ["# Backlog", "No stories here"]
        assert _parse_stories(lines) == []

    def test_empty_stories_section(self):
        lines = ["## Stories", ""]
        assert _parse_stories(lines) == []


# ── End-to-End Convert ───────────────────────────────────────────────────────


class TestConvert:
    def test_full_conversion(self):
        result = convert(BACKLOG_STORIES_SECTION)
        assert result["project"] == "TestProject"
        assert result["goal"] == "Test goal"
        assert result["dates"] == {"start": "", "end": ""}
        assert result["totalPoints"] == 0
        assert len(result["stories"]) == 2

    def test_story_structure(self):
        result = convert(BACKLOG_STORIES_SECTION)
        story = result["stories"][0]
        assert story["id"] == "US-001"
        assert story["type"] == "User Story"
        assert story["status"] == "Backlog"
        assert story["item_type"] == "story"

    def test_empty_content(self):
        result = convert("")
        assert result["project"] == ""
        assert result["goal"] == ""
        assert result["stories"] == []

    def test_matches_sample_structure_schema(self):
        """Verify output has the same top-level keys as sample_structure.json."""
        sample = json.loads(SAMPLE_JSON.read_text())
        result = convert(BACKLOG_STORIES_SECTION)

        assert set(result.keys()) == set(sample.keys())

        sample_story_keys = set(sample["stories"][0].keys())
        result_story_keys = set(result["stories"][0].keys())
        assert result_story_keys == sample_story_keys
