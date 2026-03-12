"""Tests for SessionState — session-scoped wrapper around StateStore."""

import json
from pathlib import Path

import pytest

from workflow.state_store import StateStore
from workflow.session_state import SessionState


# ─── Helpers ────────────────────────────────────────────────────────────────


def make_session_state(tmp_path: Path, initial: dict | None = None) -> SessionState:
    """Create a SessionState backed by a temp state file."""
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(initial or {}))
    return SessionState(state_path=state_file)


# ─── Create ─────────────────────────────────────────────────────────────────


class TestSessionStateCreate:
    def test_create_session_stores_under_sessions_key(self, tmp_path):
        """Creating a session stores it under sessions.<story_id>."""
        ss = make_session_state(tmp_path)
        data = {"workflow_type": "implement", "story_id": "SK-001"}
        ss.create_session("SK-001", data)

        raw = json.loads((tmp_path / "state.json").read_text())
        assert "sessions" in raw
        assert "SK-001" in raw["sessions"]
        assert raw["sessions"]["SK-001"]["story_id"] == "SK-001"

    def test_create_duplicate_overwrites(self, tmp_path):
        """Creating a session with an existing key overwrites it."""
        ss = make_session_state(tmp_path)
        ss.create_session("SK-001", {"phase": {"current": "pre-coding"}})
        ss.create_session("SK-001", {"phase": {"current": "code"}})

        session = ss.get_session("SK-001")
        assert session["phase"]["current"] == "code"


# ─── Get ────────────────────────────────────────────────────────────────────


class TestSessionStateGet:
    def test_get_existing_session(self, tmp_path):
        """get_session returns the session dict for an existing key."""
        ss = make_session_state(tmp_path)
        ss.create_session("SK-001", {"workflow_type": "implement"})

        result = ss.get_session("SK-001")
        assert result is not None
        assert result["workflow_type"] == "implement"

    def test_get_nonexistent_returns_none(self, tmp_path):
        """get_session returns None for a missing key."""
        ss = make_session_state(tmp_path)
        assert ss.get_session("SK-999") is None


# ─── Update ─────────────────────────────────────────────────────────────────


class TestSessionStateUpdate:
    def test_update_modifies_session_in_place(self, tmp_path):
        """update_session applies a function to the session dict."""
        ss = make_session_state(tmp_path)
        ss.create_session("SK-001", {"phase": {"current": "pre-coding", "previous": None}})

        ss.update_session("SK-001", lambda s: s["phase"].update({"current": "code", "previous": "pre-coding"}))

        session = ss.get_session("SK-001")
        assert session["phase"]["current"] == "code"
        assert session["phase"]["previous"] == "pre-coding"

    def test_update_nonexistent_raises(self, tmp_path):
        """update_session raises KeyError for a missing session."""
        ss = make_session_state(tmp_path)
        with pytest.raises(KeyError):
            ss.update_session("SK-999", lambda s: s.update({"x": 1}))


# ─── Delete ─────────────────────────────────────────────────────────────────


class TestSessionStateDelete:
    def test_delete_removes_session_key(self, tmp_path):
        """delete_session removes the session from state."""
        ss = make_session_state(tmp_path)
        ss.create_session("SK-001", {"workflow_type": "implement"})
        ss.delete_session("SK-001")

        assert ss.get_session("SK-001") is None

    def test_delete_nonexistent_is_noop(self, tmp_path):
        """delete_session on a missing key does not raise."""
        ss = make_session_state(tmp_path)
        ss.delete_session("SK-999")  # Should not raise


# ─── Defaults ───────────────────────────────────────────────────────────────


class TestSessionStateDefaults:
    def test_default_implement_session_has_required_keys(self):
        """default_implement_session returns a dict with all required keys."""
        session = SessionState.default_implement_session("SK-001", "test-uuid")

        assert session["session_id"] == "test-uuid"
        assert session["workflow_type"] == "implement"
        assert session["story_id"] == "SK-001"
        assert "phase" in session
        assert session["phase"]["current"] == "pre-coding"
        assert session["phase"]["previous"] is None
        assert session["phase"]["recent_agent"] is None
        assert "control" in session
        assert session["control"]["status"] == "running"
        assert session["control"]["hold"] is False
        assert session["control"]["blocked_until_phase"] is None
        assert "pr" in session
        assert session["pr"]["created"] is False
        assert session["pr"]["number"] is None
        assert "validation" in session
        assert session["validation"]["decision_invoked"] is False
        assert session["validation"]["confidence_score"] == 0
        assert session["validation"]["quality_score"] == 0
        assert session["validation"]["iteration_count"] == 0
        assert session["validation"]["escalate_to_user"] is False
        assert "ci" in session
        assert session["ci"]["status"] == "pending"
        assert session["ci"]["iteration_count"] == 0
        assert session["ci"]["escalate_to_user"] is False

    def test_default_pr_review_session_has_required_keys(self):
        """default_pr_review_session returns a dict with pr-review keys."""
        session = SessionState.default_pr_review_session(42, "test-uuid")

        assert session["session_id"] == "test-uuid"
        assert session["workflow_type"] == "pr-review"
        assert session["pr"]["created"] is True
        assert session["pr"]["number"] == 42
        assert session["phase"]["current"] == "pr-review"


# ─── Story ID from Environment ──────────────────────────────────────────────


class TestSessionStateNoStoryId:
    def test_story_id_none_when_env_not_set(self, tmp_path):
        """story_id is None when STORY_ID env var is not set."""
        ss = make_session_state(tmp_path)
        # Don't set STORY_ID — it should be None by default
        assert ss.story_id is None

    def test_story_id_reads_from_env(self, tmp_path, monkeypatch):
        """story_id reads from STORY_ID environment variable."""
        monkeypatch.setenv("STORY_ID", "SK-TEST")
        ss = make_session_state(tmp_path)
        assert ss.story_id == "SK-TEST"
