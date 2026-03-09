"""Tests for FileManager and helper functions."""

import json
from pathlib import Path

import pytest

from workflow.lib.file_manager import (
    append_text,
    load_jsonl,
    load_file,
    write_file,
    update_file,
    set_default,
    FileManager,
)


# ─── Helper function tests ──────────────────────────────────────────────────


class TestAppendText:
    def test_append_text(self, tmp_path):
        """append_text creates parent dirs and appends."""
        f = tmp_path / "sub" / "log.txt"
        append_text(f, "line1\n")
        append_text(f, "line2\n")
        assert f.read_text() == "line1\nline2\n"


class TestLoadJsonl:
    def test_load_jsonl_valid(self, tmp_path):
        """Reads multiple JSON lines."""
        f = tmp_path / "data.jsonl"
        f.write_text('{"a":1}\n{"b":2}\n')
        result = load_jsonl(f)
        assert result == [{"a": 1}, {"b": 2}]

    def test_load_jsonl_empty(self, tmp_path):
        """Empty file returns empty list."""
        f = tmp_path / "empty.jsonl"
        f.write_text("")
        assert load_jsonl(f) == []

    def test_load_jsonl_missing(self, tmp_path):
        """Missing file returns empty list."""
        f = tmp_path / "missing.jsonl"
        assert load_jsonl(f) == []


class TestLoadFile:
    def test_load_file_json(self, tmp_path):
        """Loads and parses a JSON file."""
        f = tmp_path / "data.json"
        f.write_text('{"key": "val"}')
        result = load_file(f)
        assert result == {"key": "val"}

    def test_load_file_text(self, tmp_path):
        """Loads a text file as string."""
        f = tmp_path / "note.md"
        f.write_text("hello world")
        assert load_file(f) == "hello world"

    def test_load_file_missing_with_default(self, tmp_path):
        """Missing file with default returns default without creating file."""
        f = tmp_path / "new.json"
        result = load_file(f, default={"init": True})
        assert result == {"init": True}
        assert not f.exists()

    def test_load_file_missing_without_default(self, tmp_path):
        """Missing file without default raises FileNotFoundError."""
        f = tmp_path / "new.json"
        with pytest.raises(FileNotFoundError):
            load_file(f)

    def test_load_file_corrupt_json(self, tmp_path):
        """Corrupt JSON raises ValueError."""
        f = tmp_path / "bad.json"
        f.write_text("{invalid json")
        with pytest.raises(ValueError, match="Corrupt JSON"):
            load_file(f)


class TestWriteFile:
    def test_write_file_json(self, tmp_path):
        """Writes JSON data atomically."""
        f = tmp_path / "out.json"
        write_file(f, {"key": "val"})
        result = json.loads(f.read_text())
        assert result == {"key": "val"}
        # No .tmp file left behind
        assert not (tmp_path / "out.json.tmp").exists()

    def test_write_file_text(self, tmp_path):
        """Writes text data."""
        f = tmp_path / "out.txt"
        write_file(f, "hello")
        assert f.read_text() == "hello"


class TestUpdateFile:
    def test_update_file(self, tmp_path):
        """update_file reads, modifies, and writes back."""
        f = tmp_path / "state.json"
        f.write_text('{"count": 0}')
        update_file(f, lambda d: d.update({"count": d["count"] + 1}))
        result = json.loads(f.read_text())
        assert result["count"] == 1


class TestSetDefault:
    def test_set_default_json(self):
        assert set_default(Path("x.json")) == {}

    def test_set_default_jsonl(self):
        assert set_default(Path("x.jsonl")) == []

    def test_set_default_other(self):
        assert set_default(Path("x.txt")) == ""


# ─── FileManager class tests ────────────────────────────────────────────────


class TestFileManagerCreateJson:
    def test_create_json_file_new(self, tmp_path):
        """Creates a new JSON file with default data."""
        f = tmp_path / "new.json"
        fm = FileManager(f)
        fm.create_json_file({"init": True})
        assert f.exists()
        assert json.loads(f.read_text()) == {"init": True}

    def test_create_json_file_existing(self, tmp_path):
        """Does not overwrite existing file."""
        f = tmp_path / "existing.json"
        f.write_text('{"old": true}')
        fm = FileManager(f)
        fm.create_json_file({"new": True})
        assert json.loads(f.read_text()) == {"old": True}

    def test_create_json_file_invalid_suffix(self, tmp_path):
        """Raises ValueError for non-JSON file."""
        f = tmp_path / "bad.txt"
        fm = FileManager(f)
        with pytest.raises(ValueError, match="not a JSON"):
            fm.create_json_file()


class TestFileManagerCreateJsonl:
    def test_create_jsonl_file(self, tmp_path):
        """Creates a new JSONL file."""
        f = tmp_path / "data.jsonl"
        fm = FileManager(f)
        fm.create_jsonl_file()
        assert f.exists()


class TestFileManagerLoadSave:
    def test_load_with_lock(self, tmp_path):
        """Load with locking enabled."""
        f = tmp_path / "data.json"
        f.write_text('{"a": 1}')
        fm = FileManager(f, lock=True)
        result = fm.load()
        assert result == {"a": 1}

    def test_load_without_lock(self, tmp_path):
        """Load with locking disabled."""
        f = tmp_path / "data.json"
        f.write_text('{"b": 2}')
        fm = FileManager(f, lock=False)
        result = fm.load()
        assert result == {"b": 2}

    def test_save_with_lock(self, tmp_path):
        """Save with locking enabled."""
        f = tmp_path / "data.json"
        f.touch()
        fm = FileManager(f, lock=True)
        fm.save({"saved": True})
        assert json.loads(f.read_text()) == {"saved": True}


class TestFileManagerUpdate:
    def test_update(self, tmp_path):
        """Atomic read-modify-write."""
        f = tmp_path / "state.json"
        f.write_text('{"x": 1}')
        fm = FileManager(f, lock=True)
        fm.update(lambda d: d.update({"x": 2}))
        assert json.loads(f.read_text()) == {"x": 2}


class TestFileManagerDelete:
    def test_delete(self, tmp_path):
        """delete() removes the file."""
        f = tmp_path / "del.json"
        f.write_text("{}")
        fm = FileManager(f)
        fm.delete()
        assert not f.exists()


class TestFileManagerStaticOps:
    def test_create_dir(self, tmp_path):
        d = tmp_path / "a" / "b"
        FileManager.create_dir(d)
        assert d.exists()

    def test_create_multi_dir(self, tmp_path):
        dirs = [tmp_path / "x", tmp_path / "y"]
        FileManager.create_multi_dir(dirs)
        assert all(d.exists() for d in dirs)

    def test_create_file(self, tmp_path):
        f = tmp_path / "new.json"
        FileManager.create_file(f, {"init": True})
        assert f.exists()

    def test_delete_file(self, tmp_path):
        f = tmp_path / "del.txt"
        f.touch()
        FileManager.delete_file(f)
        assert not f.exists()

    def test_delete_multi_file(self, tmp_path):
        files = [tmp_path / "a.txt", tmp_path / "b.txt"]
        for f in files:
            f.touch()
        FileManager.delete_multi_file(files)
        assert not any(f.exists() for f in files)


class TestFileManagerFalsyDefault:
    def test_create_json_file_with_list_default(self, tmp_path):
        """create_json_file(default=[]) preserves list, doesn't become {}."""
        f = tmp_path / "list.json"
        fm = FileManager(f)
        fm.create_json_file(default=[])
        import json
        assert json.loads(f.read_text()) == []

    def test_create_jsonl_file_with_empty_list(self, tmp_path):
        """create_jsonl_file(default=[]) preserves empty list."""
        f = tmp_path / "data.jsonl"
        fm = FileManager(f)
        fm.create_jsonl_file(default=[])
        assert fm._data == []


class TestFileManagerSafeDelete:
    def test_delete_nonexistent_file(self, tmp_path):
        """delete() on non-existent file doesn't raise."""
        f = tmp_path / "ghost.json"
        fm = FileManager(f)
        fm.delete()  # Should not raise

    def test_delete_file_static_nonexistent(self, tmp_path):
        """delete_file() on non-existent file doesn't raise."""
        f = tmp_path / "ghost.txt"
        FileManager.delete_file(f)  # Should not raise
