"""Tests for SessionStore — JSONL-backed session-scoped state store."""

import json
from pathlib import Path

import pytest

from workflow.session_store import SessionStore


@pytest.fixture
def jsonl_path(tmp_path):
    return tmp_path / "state.jsonl"


class TestSessionStoreLoadEmpty:
    def test_load_empty_returns_dict(self, jsonl_path):
        """Loading from a new file returns empty dict."""
        store = SessionStore("s1", jsonl_path)
        assert store.load() == {}

    def test_load_nonexistent_file(self, jsonl_path):
        """Loading when file doesn't exist returns empty dict."""
        store = SessionStore("s1", jsonl_path)
        assert store.load() == {}


class TestSessionStoreSaveAndLoad:
    def test_save_and_load_roundtrip(self, jsonl_path):
        """Save then load returns the same data (plus session_id)."""
        store = SessionStore("s1", jsonl_path)
        data = {"key": "value", "nested": {"a": 1}}
        store.save(data)
        result = store.load()
        assert result["key"] == "value"
        assert result["nested"] == {"a": 1}
        assert result["session_id"] == "s1"

    def test_save_injects_session_id(self, jsonl_path):
        """Save auto-injects session_id into the state dict."""
        store = SessionStore("s1", jsonl_path)
        store.save({"phase": "explore"})
        result = store.load()
        assert result["session_id"] == "s1"


class TestSessionStoreUpdate:
    def test_update_atomic(self, jsonl_path):
        """update() performs read-modify-write."""
        store = SessionStore("s1", jsonl_path)
        store.save({"count": 0})
        store.update(lambda d: d.update({"count": d["count"] + 1}))
        assert store.load()["count"] == 1


class TestSessionStoreGetSet:
    def test_get_set(self, jsonl_path):
        """set() writes a key, get() reads it back."""
        store = SessionStore("s1", jsonl_path)
        store.set("foo", "bar")
        assert store.get("foo") == "bar"

    def test_get_missing_returns_default(self, jsonl_path):
        """get() with missing key returns default."""
        store = SessionStore("s1", jsonl_path)
        assert store.get("missing", "fallback") == "fallback"


class TestSessionStoreReset:
    def test_reset_clears_state(self, jsonl_path):
        """reset() clears to empty dict (with session_id)."""
        store = SessionStore("s1", jsonl_path)
        store.save({"key": "val"})
        store.reset()
        result = store.load()
        assert "key" not in result
        assert result["session_id"] == "s1"


class TestSessionStoreReinitialize:
    def test_reinitialize_replaces_state(self, jsonl_path):
        """reinitialize() replaces the entire session state."""
        store = SessionStore("s1", jsonl_path)
        store.save({"old_key": "old_val"})
        store.reinitialize({"new_key": "new_val"})
        result = store.load()
        assert "old_key" not in result
        assert result["new_key"] == "new_val"
        assert result["session_id"] == "s1"


class TestSessionStoreDelete:
    def test_delete_removes_session(self, jsonl_path):
        """delete() removes the session's line from JSONL."""
        store = SessionStore("s1", jsonl_path)
        store.save({"key": "val"})
        store.delete()
        assert store.load() == {}

    def test_delete_preserves_other_sessions(self, jsonl_path):
        """delete() only removes the target session."""
        s1 = SessionStore("s1", jsonl_path)
        s2 = SessionStore("s2", jsonl_path)
        s1.save({"phase": "explore"})
        s2.save({"phase": "plan"})
        s1.delete()
        assert s1.load() == {}
        assert s2.load()["phase"] == "plan"


class TestSessionIsolation:
    def test_sessions_are_isolated(self, jsonl_path):
        """Two sessions in the same JSONL don't see each other's state."""
        s1 = SessionStore("s1", jsonl_path)
        s2 = SessionStore("s2", jsonl_path)
        s1.save({"phase": "explore", "workflow_active": True})
        s2.save({"phase": "plan", "workflow_active": True})

        assert s1.load()["phase"] == "explore"
        assert s2.load()["phase"] == "plan"

    def test_update_one_session_does_not_affect_other(self, jsonl_path):
        """Updating one session leaves the other unchanged."""
        s1 = SessionStore("s1", jsonl_path)
        s2 = SessionStore("s2", jsonl_path)
        s1.save({"count": 0})
        s2.save({"count": 100})
        s1.update(lambda d: d.update({"count": d["count"] + 1}))
        assert s1.load()["count"] == 1
        assert s2.load()["count"] == 100

    def test_reinitialize_one_preserves_other(self, jsonl_path):
        """reinitialize() on one session doesn't touch the other."""
        s1 = SessionStore("s1", jsonl_path)
        s2 = SessionStore("s2", jsonl_path)
        s1.save({"phase": "explore"})
        s2.save({"phase": "plan"})
        s1.reinitialize({"phase": "reset"})
        assert s1.load()["phase"] == "reset"
        assert s2.load()["phase"] == "plan"


class TestCleanupInactive:
    def test_cleanup_removes_inactive(self, jsonl_path):
        """cleanup_inactive() removes sessions with workflow_active=False."""
        s1 = SessionStore("s1", jsonl_path)
        s2 = SessionStore("s2", jsonl_path)
        s1.save({"workflow_active": True, "phase": "explore"})
        s2.save({"workflow_active": False, "phase": "completed"})

        removed = SessionStore.cleanup_inactive(jsonl_path)
        assert removed == 1
        assert s1.load()["phase"] == "explore"
        assert s2.load() == {}

    def test_cleanup_keeps_active(self, jsonl_path):
        """cleanup_inactive() keeps all active sessions."""
        s1 = SessionStore("s1", jsonl_path)
        s2 = SessionStore("s2", jsonl_path)
        s1.save({"workflow_active": True})
        s2.save({"workflow_active": True})

        removed = SessionStore.cleanup_inactive(jsonl_path)
        assert removed == 0

    def test_cleanup_on_empty_file(self, jsonl_path):
        """cleanup_inactive() on empty/nonexistent file returns 0."""
        removed = SessionStore.cleanup_inactive(jsonl_path)
        assert removed == 0


class TestCorruptLines:
    def test_corrupt_line_is_skipped(self, jsonl_path):
        """Corrupt JSON lines are silently skipped."""
        jsonl_path.write_text(
            'not valid json\n'
            '{"session_id":"s1","phase":"explore"}\n'
        )
        store = SessionStore("s1", jsonl_path)
        assert store.load()["phase"] == "explore"
