"""Tests for utils/initializer.py — arg parsing, conflict detection, state init."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow.utils.initializer import (
    parse_skip,
    parse_story_id,
    parse_instructions,
    check_story_conflict,
    build_initial_state,
    initialize,
)
from workflow.session_store import SessionStore


# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------


class TestParseSkip:
    def test_no_flags(self):
        assert parse_skip("SK-123 --tdd") == []

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


class TestParseStoryId:
    def test_extracts_story_id(self):
        assert parse_story_id("SK-123 --tdd") == "SK-123"

    def test_no_story_id(self):
        assert parse_story_id("--tdd --skip-all") is None

    def test_multiple_ids_takes_first(self):
        assert parse_story_id("SK-001 SK-002") == "SK-001"


class TestParseInstructions:
    def test_strips_flags_and_story_id(self):
        result = parse_instructions("SK-123 --tdd --skip-all implement login flow")
        assert result == "implement login flow"

    def test_empty_when_only_flags(self):
        assert parse_instructions("SK-123 --tdd") == ""

    def test_preserves_free_text(self):
        assert parse_instructions("add dark mode support") == "add dark mode support"


# ---------------------------------------------------------------------------
# Conflict check
# ---------------------------------------------------------------------------


class TestStoryConflictCheck:
    def test_no_conflict(self, tmp_path):
        jsonl = tmp_path / "state.jsonl"
        jsonl.write_text('{"session_id":"other","workflow_active":true,"story_id":"SK-999"}\n')
        # Should not exit
        check_story_conflict("SK-123", "my-session", jsonl)

    def test_conflict_exits_2(self, tmp_path):
        jsonl = tmp_path / "state.jsonl"
        jsonl.write_text('{"session_id":"other","workflow_active":true,"story_id":"SK-123"}\n')
        with pytest.raises(SystemExit) as exc_info:
            check_story_conflict("SK-123", "my-session", jsonl)
        assert exc_info.value.code == 2

    def test_same_session_not_conflict(self, tmp_path):
        jsonl = tmp_path / "state.jsonl"
        jsonl.write_text('{"session_id":"my-session","workflow_active":true,"story_id":"SK-123"}\n')
        # Same session should not conflict
        check_story_conflict("SK-123", "my-session", jsonl)

    def test_inactive_session_not_conflict(self, tmp_path):
        jsonl = tmp_path / "state.jsonl"
        jsonl.write_text('{"session_id":"other","workflow_active":false,"story_id":"SK-123"}\n')
        check_story_conflict("SK-123", "my-session", jsonl)

    def test_empty_story_id_skips(self, tmp_path):
        jsonl = tmp_path / "state.jsonl"
        jsonl.write_text('{"session_id":"other","workflow_active":true,"story_id":"SK-123"}\n')
        check_story_conflict("", "my-session", jsonl)

    def test_missing_file_skips(self, tmp_path):
        jsonl = tmp_path / "nonexistent.jsonl"
        check_story_conflict("SK-123", "my-session", jsonl)


# ---------------------------------------------------------------------------
# Build initial state
# ---------------------------------------------------------------------------


class TestBuildInitialState:
    def test_implement_default(self):
        state = build_initial_state("implement", "SK-123 --tdd")
        assert state["workflow_active"] is True
        assert state["workflow_type"] == "implement"
        assert state["phase"] == "explore"
        assert state["tdd"] is True
        assert state["story_id"] == "SK-123"
        assert state["skip"] == []

    def test_implement_skip_all(self):
        state = build_initial_state("implement", "SK-123 --skip-all")
        assert state["phase"] == "plan"
        assert "explore" in state["skip"]
        assert "research" in state["skip"]

    def test_plan_no_story_id(self):
        state = build_initial_state("plan", "--skip-all fix the bug")
        assert state["story_id"] is None
        assert state["workflow_type"] == "plan"
        assert "fix the bug" in state["instructions"]

    def test_nested_plan_structure(self):
        state = build_initial_state("implement", "SK-001")
        assert state["plan"]["file_path"] is None
        assert state["plan"]["written"] is False
        assert state["plan"]["review"]["iteration"] == 0

    def test_nested_tests_structure(self):
        state = build_initial_state("implement", "SK-001")
        assert state["tests"]["file_paths"] == []
        assert state["tests"]["review_result"] is None
        assert state["tests"]["executed"] is False


# ---------------------------------------------------------------------------
# Full initialize
# ---------------------------------------------------------------------------


class TestInitialize:
    def test_writes_state_to_store(self, tmp_state_file):
        initialize("implement", "s", "SK-123 --tdd", tmp_state_file)
        state = SessionStore("s", tmp_state_file).load()
        assert state["workflow_active"] is True
        assert state["story_id"] == "SK-123"
        assert state["tdd"] is True

    def test_plan_initialize(self, tmp_state_file):
        initialize("plan", "s", "--skip-all", tmp_state_file)
        state = SessionStore("s", tmp_state_file).load()
        assert state["workflow_type"] == "plan"
        assert state["phase"] == "plan"
        assert state["story_id"] is None

    def test_conflict_blocks_initialize(self, tmp_state_file):
        # Write an active session with SK-123
        other_state = {"session_id": "other", "workflow_active": True, "story_id": "SK-123"}
        SessionStore("other", tmp_state_file).save(other_state)

        with pytest.raises(SystemExit) as exc_info:
            initialize("implement", "my-session", "SK-123", tmp_state_file)
        assert exc_info.value.code == 2

    def test_reinitializes_existing_session(self, tmp_state_file):
        # First init
        initialize("implement", "s", "SK-001", tmp_state_file)
        state1 = SessionStore("s", tmp_state_file).load()
        assert state1["story_id"] == "SK-001"

        # Re-init same session with different story
        initialize("implement", "s", "SK-002", tmp_state_file)
        state2 = SessionStore("s", tmp_state_file).load()
        assert state2["story_id"] == "SK-002"
