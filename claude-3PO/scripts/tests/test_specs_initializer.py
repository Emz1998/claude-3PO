"""Tests for specs workflow initialization — minimal docs-based schema."""

import json
import pytest
from pathlib import Path

from utils.initializer import build_initial_state, initialize


class TestSpecsInitialState:
    def test_returns_docs_field(self):
        state = build_initial_state("specs", "sess-1", "")
        assert "docs" in state

    def test_docs_has_product_vision(self):
        state = build_initial_state("specs", "sess-1", "")
        pv = state["docs"]["product_vision"]
        assert pv == {"written": False, "path": ""}

    def test_docs_has_decisions(self):
        state = build_initial_state("specs", "sess-1", "")
        assert state["docs"]["decisions"] == {"written": False, "path": ""}

    def test_docs_has_architecture(self):
        state = build_initial_state("specs", "sess-1", "")
        assert state["docs"]["architecture"] == {"written": False, "path": ""}

    def test_docs_has_backlog(self):
        state = build_initial_state("specs", "sess-1", "")
        bl = state["docs"]["backlog"]
        assert bl == {"written": False, "md_path": "", "json_path": ""}

    def test_has_core_fields(self):
        state = build_initial_state("specs", "sess-1", "build something")
        assert state["session_id"] == "sess-1"
        assert state["workflow_active"] is True
        assert state["status"] == "in_progress"
        assert state["workflow_type"] == "specs"
        assert state["phases"] == []
        assert state["agents"] == []
        assert state["skip"] == []
        assert state["instructions"] == "build something"

    def test_no_build_fields(self):
        state = build_initial_state("specs", "sess-1", "")
        for key in ("tdd", "story_id", "plan", "tests", "code_files",
                     "quality_check_result", "pr", "ci-check", "report_written",
                     "contracts", "dependencies", "tasks", "code_files_to_write"):
            assert key not in state, f"specs state should not have '{key}'"

    def test_all_schema_keys(self):
        state = build_initial_state("specs", "sess-1", "")
        expected = {
            "session_id", "workflow_active", "status", "workflow_type",
            "test_mode", "phases", "agents", "skip", "instructions", "docs",
        }
        assert set(state.keys()) == expected

    def test_test_mode_default_false(self):
        state = build_initial_state("specs", "sess-1", "")
        assert state["test_mode"] is False

    def test_test_mode_flag(self):
        state = build_initial_state("specs", "sess-1", "--test create specs")
        assert state["test_mode"] is True

    def test_skip_flag(self):
        state = build_initial_state("specs", "sess-1", "--skip-vision")
        assert "vision" in state["skip"]


class TestSpecsInitialize:
    def test_skips_archive_and_story_guard(self, tmp_path: Path):
        state_path = tmp_path / "state.jsonl"
        state_path.write_text("")
        # Should not raise even though there's no plan to archive
        initialize("specs", "sess-1", "create specs", state_path)
        content = state_path.read_text().strip()
        entry = json.loads(content.splitlines()[0])
        assert entry["workflow_type"] == "specs"
        assert "docs" in entry
        assert "plan" not in entry
