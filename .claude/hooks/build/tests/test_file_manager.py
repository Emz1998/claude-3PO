"""Tests for FileManager and helper functions."""

import json
from pathlib import Path

import pytest

from build.lib.file_manager import (
    create_file,
    load_file,
    save_file,
    update_file,
    FileManager,
)


# ─── Helper function tests ──────────────────────────────────────────────────


class TestCreateFile:
    def test_create_json_file(self, tmp_path):
        f = tmp_path / "new.json"
        create_file(f)
        assert f.exists()
        assert json.loads(f.read_text()) == {}

    def test_create_json_file_with_default(self, tmp_path):
        f = tmp_path / "new.json"
        create_file(f, default={"init": True})
        assert json.loads(f.read_text()) == {"init": True}

    def test_create_non_json_file(self, tmp_path):
        f = tmp_path / "log.txt"
        create_file(f)
        assert f.exists()
        assert f.read_text() == ""

    def test_create_file_makes_parents(self, tmp_path):
        f = tmp_path / "sub" / "dir" / "data.json"
        create_file(f)
        assert f.exists()


class TestLoadFile:
    def test_load_json(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"key": "val"}')
        assert load_file(f) == {"key": "val"}

    def test_load_missing_creates_empty(self, tmp_path):
        f = tmp_path / "new.json"
        result = load_file(f)
        assert result == {}
        assert f.exists()

    def test_load_empty_returns_empty_dict(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("")
        assert load_file(f) == {}

    def test_load_corrupt_json_raises(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{invalid json")
        with pytest.raises(ValueError, match="Corrupt JSON"):
            load_file(f)


class TestSaveFile:
    def test_save_json(self, tmp_path):
        f = tmp_path / "out.json"
        save_file({"key": "val"}, "w", f)
        assert json.loads(f.read_text()) == {"key": "val"}

    def test_save_text(self, tmp_path):
        f = tmp_path / "out.txt"
        save_file("hello", "w", f)
        assert f.read_text() == "hello"

    def test_save_append(self, tmp_path):
        f = tmp_path / "log.txt"
        save_file("line1\n", "w", f)
        save_file("line2\n", "a", f)
        assert f.read_text() == "line1\nline2\n"


class TestUpdateFile:
    def test_update_file(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text('{"count": 0}')
        update_file(f, lambda d: d.update({"count": d["count"] + 1}))
        assert json.loads(f.read_text()) == {"count": 1}


# ─── FileManager class tests ────────────────────────────────────────────────


class TestFileManagerCreateFile:
    def test_create_json(self, tmp_path):
        f = tmp_path / "new.json"
        fm = FileManager(f)
        fm.create_file({"init": True})
        assert f.exists()
        assert json.loads(f.read_text()) == {"init": True}

    def test_create_non_json(self, tmp_path):
        f = tmp_path / "log.txt"
        fm = FileManager(f)
        fm.create_file()
        assert f.exists()


class TestFileManagerLoadSave:
    def test_load_with_lock(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"a": 1}')
        fm = FileManager(f, lock=True)
        assert fm.load_file() == {"a": 1}

    def test_load_without_lock(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"b": 2}')
        fm = FileManager(f, lock=False)
        assert fm.load_file() == {"b": 2}

    def test_save(self, tmp_path):
        f = tmp_path / "data.json"
        f.touch()
        fm = FileManager(f)
        fm.save_file({"saved": True})
        assert json.loads(f.read_text()) == {"saved": True}


class TestFileManagerUpdate:
    def test_update(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text('{"x": 1}')
        fm = FileManager(f, lock=True)
        fm.update_file(lambda d: d.update({"x": 2}))
        assert json.loads(f.read_text()) == {"x": 2}


class TestFileManagerDelete:
    def test_delete(self, tmp_path):
        f = tmp_path / "del.json"
        f.write_text("{}")
        fm = FileManager(f)
        fm.delete_file()
        assert not f.exists()
