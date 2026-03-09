"""Tests for StateStore — JSON state with file locking."""

import json
from pathlib import Path

import pytest

from workflow.state_store import StateStore


class TestStateStoreLoadEmpty:
    def test_load_empty_returns_dict(self, tmp_path):
        """Loading from a new file returns empty dict."""
        store = StateStore(tmp_path / "state.json")
        result = store.load()
        assert result == {}


class TestStateStoreSaveAndLoad:
    def test_save_and_load_roundtrip(self, tmp_path):
        """Save then load returns the same data."""
        store = StateStore(tmp_path / "state.json")
        data = {"key": "value", "nested": {"a": 1}}
        store.save(data)
        result = store.load()
        assert result == data


class TestStateStoreUpdate:
    def test_update_atomic(self, tmp_path):
        """update() performs read-modify-write atomically."""
        store = StateStore(tmp_path / "state.json", default_state={"count": 0})
        store.update(lambda d: d.update({"count": d["count"] + 1}))
        result = store.load()
        assert result["count"] == 1


class TestStateStoreGetSet:
    def test_get_set(self, tmp_path):
        """set() writes a key, get() reads it back."""
        store = StateStore(tmp_path / "state.json")
        store.set("foo", "bar")
        assert store.get("foo") == "bar"

    def test_get_missing_returns_default(self, tmp_path):
        """get() with missing key returns default."""
        store = StateStore(tmp_path / "state.json")
        assert store.get("missing", "fallback") == "fallback"


class TestStateStoreReset:
    def test_reset_clears_state(self, tmp_path):
        """reset() clears to empty dict."""
        store = StateStore(tmp_path / "state.json", default_state={"key": "val"})
        store.reset()
        result = store.load()
        assert result == {}


class TestStateStoreDelete:
    def test_delete_removes_file(self, tmp_path):
        """delete() removes the state file."""
        store = StateStore(tmp_path / "state.json")
        store.delete()
        assert not (tmp_path / "state.json").exists()


class TestStateStoreArchive:
    def test_archive_appends_jsonl(self, tmp_path):
        """archive() appends current state as JSONL entry."""
        state_file = tmp_path / "state.json"
        history_file = tmp_path / "history.jsonl"
        history_file.touch()

        store = StateStore(state_file, default_state={"phase": "explore"})
        store.archive(history_file)

        text = history_file.read_text()
        assert text.strip() != ""
        entry = json.loads(text.strip())
        assert entry["phase"] == "explore"


class TestStateStoreLatestFromHistory:
    def test_latest_from_history(self, tmp_path):
        """latest_from_history() reads from a JSON history file (list of entries)."""
        history_file = tmp_path / "history.json"
        entries = [{"phase": "explore"}, {"phase": "plan"}]
        history_file.write_text(json.dumps(entries))

        result = StateStore.latest_from_history(history_file)
        assert result == {"phase": "plan"}

    def test_latest_from_history_jsonl_returns_none(self, tmp_path):
        """latest_from_history() on .jsonl returns None (loads as text, not list)."""
        state_file = tmp_path / "state.json"
        history_file = tmp_path / "history.jsonl"
        history_file.touch()

        store = StateStore(state_file, default_state={"phase": "explore"})
        store.archive(history_file)

        # JSONL files are loaded as text by FileManager, so returns None
        result = StateStore.latest_from_history(history_file)
        assert result is None

    def test_latest_from_history_empty(self, tmp_path):
        """Empty history returns None."""
        history_file = tmp_path / "history.jsonl"
        history_file.write_text("")
        result = StateStore.latest_from_history(history_file)
        assert result is None
