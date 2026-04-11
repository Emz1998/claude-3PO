"""Tests for utils/initializer.py — arg parsing and state initialization."""

import json
import pytest
from pathlib import Path

from utils.initializer import (
    parse_skip,
    parse_story_id,
    parse_instructions,
    build_initial_state,
    initialize,
)


# ═══════════════════════════════════════════════════════════════════
# parse_skip
# ═══════════════════════════════════════════════════════════════════


class TestParseSkip:
    def test_no_flags(self):
        assert parse_skip("build a login form") == []

    def test_skip_explore(self):
        assert parse_skip("--skip-explore build a login form") == ["explore"]

    def test_skip_research(self):
        assert parse_skip("--skip-research build a login form") == ["research"]

    def test_skip_all(self):
        assert parse_skip("--skip-all build a login form") == ["explore", "research"]

    def test_skip_explore_and_research(self):
        result = parse_skip("--skip-explore --skip-research build")
        assert result == ["explore", "research"]

    def test_empty_args(self):
        assert parse_skip("") == []


# ═══════════════════════════════════════════════════════════════════
# parse_story_id
# ═══════════════════════════════════════════════════════════════════


class TestParseStoryId:
    def test_extracts_story_id(self):
        assert parse_story_id("SK-001 build a login form") == "SK-001"

    def test_extracts_story_id_mid_string(self):
        assert parse_story_id("--tdd FEAT-42 build a form") == "FEAT-42"

    def test_no_story_id(self):
        assert parse_story_id("build a login form") is None

    def test_empty_args(self):
        assert parse_story_id("") is None

    def test_multiple_ids_returns_first(self):
        assert parse_story_id("SK-001 BUG-002") == "SK-001"


# ═══════════════════════════════════════════════════════════════════
# parse_instructions
# ═══════════════════════════════════════════════════════════════════


class TestParseInstructions:
    def test_strips_flags(self):
        result = parse_instructions("--tdd --skip-all build a login form")
        assert result == "build a login form"

    def test_strips_story_id(self):
        result = parse_instructions("SK-001 build a login form")
        assert result == "build a login form"

    def test_strips_all(self):
        result = parse_instructions("--tdd --skip-explore SK-001 build a login form")
        assert result == "build a login form"

    def test_no_flags_no_id(self):
        result = parse_instructions("build a login form")
        assert result == "build a login form"

    def test_only_flags(self):
        result = parse_instructions("--tdd --skip-all")
        assert result == ""

    def test_empty(self):
        assert parse_instructions("") == ""


# ═══════════════════════════════════════════════════════════════════
# build_initial_state
# ═══════════════════════════════════════════════════════════════════


class TestBuildInitialState:
    def test_default_state(self):
        state = build_initial_state("implement", "sess-1", "build a form")
        assert state["session_id"] == "sess-1"
        assert state["workflow_active"] is True
        assert state["workflow_type"] == "implement"
        assert state["tdd"] is False
        assert state["story_id"] is None
        assert state["skip"] == []
        assert state["instructions"] == "build a form"
        assert state["phases"] == []

    def test_tdd_flag(self):
        state = build_initial_state("implement", "sess-1", "--tdd build a form")
        assert state["tdd"] is True

    def test_skip_all(self):
        state = build_initial_state("implement", "sess-1", "--skip-all build a form")
        assert state["phases"] == []
        assert state["skip"] == ["explore", "research"]

    def test_skip_explore_only(self):
        state = build_initial_state("implement", "sess-1", "--skip-explore build")
        assert state["phases"] == []

    def test_story_id_extracted(self):
        state = build_initial_state("implement", "sess-1", "SK-001 build a form")
        assert state["story_id"] == "SK-001"

    def test_all_schema_keys_present(self):
        state = build_initial_state("implement", "sess-1", "")
        expected_keys = {
            "session_id", "workflow_active", "workflow_type", "phases",
            "sub_phases", "tdd", "story_id", "skip", "instructions",
            "agents", "plan", "tasks", "tests", "code_files_to_write",
            "code_files", "quality_check_result", "pr", "ci-check",
            "report_written",
        }
        assert set(state.keys()) == expected_keys

    def test_nested_defaults(self):
        state = build_initial_state("implement", "sess-1", "")
        assert state["plan"]["written"] is False
        assert state["plan"]["review"]["iteration"] == 0
        assert state["tests"]["executed"] is False
        assert state["code_files"]["file_paths"] == []
        assert state["pr"]["status"] == "pending"
        assert state["ci-check"]["status"] == "pending"
        assert state["report_written"] is False


# ═══════════════════════════════════════════════════════════════════
# initialize (integration)
# ═══════════════════════════════════════════════════════════════════


class TestInitialize:
    def test_writes_state_file(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state_path.write_text("{}")
        initialize("implement", "sess-1", "--tdd SK-001 build a form", state_path)

        state = json.loads(state_path.read_text())
        assert state["session_id"] == "sess-1"
        assert state["workflow_active"] is True
        assert state["tdd"] is True
        assert state["story_id"] == "SK-001"
        assert state["instructions"] == "build a form"

    def test_reinitializes_existing_state(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"session_id": "old", "workflow_active": False}))
        initialize("implement", "new-sess", "build", state_path)

        state = json.loads(state_path.read_text())
        assert state["session_id"] == "new-sess"
        assert state["workflow_active"] is True
