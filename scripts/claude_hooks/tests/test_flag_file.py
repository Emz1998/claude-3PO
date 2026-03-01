"""Tests for the generic FlagFile module."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.claude_hooks.flag_file import FlagFile, FLAG_DIR


@pytest.fixture
def tmp_flag(tmp_path):
    """Create a FlagFile pointing at tmp_path instead of project/tmp/."""
    flag = FlagFile("test_flag")
    flag._path = tmp_path / "test_flag.json"
    return flag


class TestFlagFileExists:
    def test_exists_false_when_no_file(self, tmp_flag):
        assert tmp_flag.exists() is False

    def test_exists_true_when_file_present(self, tmp_flag):
        tmp_flag._path.write_text("{}")
        assert tmp_flag.exists() is True


class TestFlagFileRead:
    def test_read_returns_none_when_absent(self, tmp_flag):
        assert tmp_flag.read() is None

    def test_read_returns_dict_when_present(self, tmp_flag):
        tmp_flag._path.write_text(json.dumps({"key": "val"}))
        result = tmp_flag.read()
        assert result == {"key": "val"}


class TestFlagFileWrite:
    def test_write_creates_file(self, tmp_flag):
        tmp_flag.write({"foo": "bar"})
        assert tmp_flag._path.exists()
        assert json.loads(tmp_flag._path.read_text()) == {"foo": "bar"}

    def test_write_overwrites_existing(self, tmp_flag):
        tmp_flag.write({"a": 1})
        tmp_flag.write({"b": 2})
        assert json.loads(tmp_flag._path.read_text()) == {"b": 2}


class TestFlagFileUpdate:
    def test_update_creates_file_with_key(self, tmp_flag):
        result = tmp_flag.update("name", "alice")
        assert result == {"name": "alice"}
        assert tmp_flag.exists()

    def test_update_preserves_existing_keys(self, tmp_flag):
        tmp_flag.write({"existing": True})
        result = tmp_flag.update("new_key", 42)
        assert result == {"existing": True, "new_key": 42}

    def test_update_overwrites_same_key(self, tmp_flag):
        tmp_flag.update("k", "v1")
        result = tmp_flag.update("k", "v2")
        assert result == {"k": "v2"}


class TestFlagFileAppendTo:
    def test_append_to_creates_list(self, tmp_flag):
        result = tmp_flag.append_to("items", "a")
        assert result == {"items": ["a"]}

    def test_append_to_accumulates(self, tmp_flag):
        tmp_flag.append_to("items", "a")
        result = tmp_flag.append_to("items", "b")
        assert result == {"items": ["a", "b"]}

    def test_append_to_deduplicates(self, tmp_flag):
        tmp_flag.append_to("items", "a")
        result = tmp_flag.append_to("items", "a")
        assert result == {"items": ["a"]}

    def test_append_to_preserves_other_keys(self, tmp_flag):
        tmp_flag.update("story", "TS-001")
        result = tmp_flag.append_to("tasks", "T-001")
        assert result == {"story": "TS-001", "tasks": ["T-001"]}


class TestFlagFileRemoveFrom:
    def test_remove_from_removes_value(self, tmp_flag):
        tmp_flag.append_to("items", "a")
        tmp_flag.append_to("items", "b")
        result = tmp_flag.remove_from("items", "a")
        assert result == {"items": ["b"]}

    def test_remove_from_noop_when_absent(self, tmp_flag):
        tmp_flag.append_to("items", "a")
        result = tmp_flag.remove_from("items", "z")
        assert result == {"items": ["a"]}

    def test_remove_from_empty_list(self, tmp_flag):
        tmp_flag.write({"items": []})
        result = tmp_flag.remove_from("items", "a")
        assert result == {"items": []}

    def test_remove_from_missing_key(self, tmp_flag):
        tmp_flag.write({"other": "val"})
        result = tmp_flag.remove_from("items", "a")
        assert result == {"other": "val", "items": []}

    def test_remove_from_preserves_other_keys(self, tmp_flag):
        tmp_flag.update("story", "TS-001")
        tmp_flag.append_to("tasks", "T-001")
        tmp_flag.append_to("tasks", "T-002")
        result = tmp_flag.remove_from("tasks", "T-001")
        assert result == {"story": "TS-001", "tasks": ["T-002"]}


class TestFlagFileRemove:
    def test_remove_deletes_file(self, tmp_flag):
        tmp_flag.write({"data": True})
        assert tmp_flag.exists()
        tmp_flag.remove()
        assert not tmp_flag.exists()

    def test_remove_deletes_lock_file(self, tmp_flag):
        tmp_flag.write({"data": True})
        lock = tmp_flag._path.with_suffix(".lock")
        lock.write_text("")
        tmp_flag.remove()
        assert not lock.exists()

    def test_remove_noop_when_absent(self, tmp_flag):
        tmp_flag.remove()  # should not raise

    def test_read_returns_none_after_remove(self, tmp_flag):
        tmp_flag.write({"x": 1})
        tmp_flag.remove()
        assert tmp_flag.read() is None


class TestFlagFilePath:
    def test_path_property(self):
        flag = FlagFile("my_flag")
        assert flag.path == FLAG_DIR / "my_flag.json"

    def test_different_names_different_paths(self):
        a = FlagFile("alpha")
        b = FlagFile("beta")
        assert a.path != b.path
