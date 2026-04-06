"""Tests for utils/initializer.py — arg parsing and state init for /build command."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from build.utils.initializer import (
    parse_skip,
    parse_instructions,
    build_initial_state,
    initialize,
)
from build.session_store import SessionStore


# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------


class TestParseSkip:
    def test_no_flags(self):
        assert parse_skip("--tdd build a login form") == []

    def test_skip_explore(self):
        assert parse_skip("--skip-explore") == ["explore"]

    def test_skip_research(self):
        assert parse_skip("--skip-research") == ["research"]

    def test_skip_all(self):
        result = parse_skip("--skip-all")
        assert "explore" in result
        assert "research" in result

    def test_both_flags(self):
        result = parse_skip("--skip-explore --skip-research")
        assert "explore" in result
        assert "research" in result


class TestParseInstructions:
    def test_strips_flags(self):
        result = parse_instructions("--tdd --skip-all implement login flow")
        assert result == "implement login flow"

    def test_empty_when_only_flags(self):
        assert parse_instructions("--tdd") == ""

    def test_preserves_free_text(self):
        assert parse_instructions("add dark mode support") == "add dark mode support"


# ---------------------------------------------------------------------------
# Build initial state
# ---------------------------------------------------------------------------


class TestBuildInitialState:
    def test_build_default(self):
        state = build_initial_state("build", "--tdd build a login form")
        assert state["workflow_active"] is True
        assert state["workflow_type"] == "build"
        assert state["phase"] == "explore"
        assert state["tdd"] is True
        assert state["story_id"] is None
        assert state["skip"] == []
        assert state["instructions"] == "build a login form"

    def test_build_skip_all(self):
        state = build_initial_state("build", "--skip-all build something")
        assert state["phase"] == "plan"
        assert "explore" in state["skip"]
        assert "research" in state["skip"]

    def test_story_id_always_none(self):
        state = build_initial_state("build", "SK-123 build something")
        assert state["story_id"] is None

    def test_nested_plan_structure(self):
        state = build_initial_state("build", "do something")
        assert state["plan"]["file_path"] is None
        assert state["plan"]["written"] is False
        assert state["plan"]["review"]["iteration"] == 0

    def test_nested_tests_structure(self):
        state = build_initial_state("build", "do something")
        assert state["tests"]["file_paths"] == []
        assert state["tests"]["review_result"] is None
        assert state["tests"]["executed"] is False


# ---------------------------------------------------------------------------
# Full initialize
# ---------------------------------------------------------------------------


class TestInitialize:
    def test_writes_state_to_store(self, tmp_state_file):
        initialize("build", "s", "--tdd build a form", tmp_state_file)
        state = SessionStore("s", tmp_state_file).load()
        assert state["workflow_active"] is True
        assert state["story_id"] is None
        assert state["tdd"] is True
        assert state["workflow_type"] == "build"

    def test_build_skip_all(self, tmp_state_file):
        initialize("build", "s", "--skip-all do something", tmp_state_file)
        state = SessionStore("s", tmp_state_file).load()
        assert state["workflow_type"] == "build"
        assert state["phase"] == "plan"
        assert state["story_id"] is None

    def test_reinitializes_existing_session(self, tmp_state_file):
        initialize("build", "s", "first task", tmp_state_file)
        state1 = SessionStore("s", tmp_state_file).load()
        assert state1["instructions"] == "first task"

        initialize("build", "s", "second task", tmp_state_file)
        state2 = SessionStore("s", tmp_state_file).load()
        assert state2["instructions"] == "second task"
