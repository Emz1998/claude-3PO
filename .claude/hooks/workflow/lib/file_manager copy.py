"""FileManager with file locking for JSON/JSONL files."""

import json
import os
from pathlib import Path
from typing import Any, Callable
from filelock import FileLock, BaseFileLock
import sys

_JSON_SUFFIXES = {".json", ".jsonl"}


def append_text(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        print(f"Error appending to file: {e}")
        print(f"Error appendsing to file: {e}")
        sys.exit(1)


def load_jsonl(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return []
        return [json.loads(line) for line in text.strip().splitlines() if line.strip()]
    except (OSError, TypeError):
        return []


def load_file(path: Path, default: Any | None = None) -> Any | None:
    try:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            return json.loads(text) if text.strip() else default
        return text
    except FileNotFoundError:
        if default is not None:
            return default
        raise
    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupt JSON in {path}: {e}") from e


def write_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    content = json.dumps(data, indent=2) if path.suffix == ".json" else str(data)
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def update_file(path: Path, fn: Callable[[Any], None]) -> None:
    data = load_file(path, default=set_default(path))
    fn(data)
    write_file(path, data)


def set_default(path: Path):
    if path.suffix == ".json":
        return {}
    if path.suffix == ".jsonl":
        return []
    return ""


class FileManager:
    def __init__(self, path: Path, lock: bool = True):
        self._path = path
        self._use_lock = lock
        self._lock: BaseFileLock | None = self.create_file_lock() if lock else None
        self._data: Any | None = None

    def create_json_file(self, default: Any | None = None) -> None:
        if self._path.suffix not in _JSON_SUFFIXES:
            raise ValueError(f"File {self._path} is not a JSON file")

        if self._path.exists():
            return

        if not self._path.parent.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)

        self._path.touch()
        self._data = default if default is not None else {}

        write_file(self._path, self._data)

    def create_jsonl_file(self, default: Any | None = None) -> None:
        if self._path.suffix not in _JSON_SUFFIXES:
            raise ValueError(f"File {self._path} is not a JSONL file")
        self._path.touch()
        self._data = default if default is not None else []

        write_file(self._path, self._data)

    def create_file_lock(self, path: Path | None = None) -> BaseFileLock | None:
        if not self._use_lock:
            return None
        if path is None:
            path = self._path
        file_lock = FileLock(path.with_suffix(".lock"))
        return file_lock

    def load(self, default: Any | None = None) -> Any | None:
        lock = self._lock

        if not self._use_lock or lock is None:
            self._data = load_file(self._path, default)
            return self._data

        with lock:
            self._data = load_file(self._path, default)
            return self._data

    def save(self, data: Any | None = None) -> None:
        if data is None:
            data = self._data
        if not self._use_lock or self._lock is None:
            write_file(self._path, data)
            return
        with self._lock:
            write_file(self._path, data)

    def update(self, fn: Callable[[Any], None]) -> None:
        """Atomic read-modify-write."""
        if not self._use_lock or self._lock is None:
            update_file(self._path, fn)
            return
        with self._lock:
            update_file(self._path, fn)

    def append(self, data: Any | None = None, path: Path | None = None) -> None:
        if data is None:
            print("No data to append")
            return
        if path is None:
            path = self._path
        lock = self.create_file_lock(path)
        if lock is None:
            append_text(path, data)
            return
        with lock:
            append_text(path, data)

    def delete(self) -> None:
        self._path.unlink(missing_ok=True)

    @staticmethod
    def create_dir(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_multi_dir(list_of_paths: list[Path]) -> None:
        for path in list_of_paths:
            FileManager.create_dir(path)

    @staticmethod
    def create_file(path: Path, initial_data: Any | None = None) -> None:
        path.touch()
        write_file(path, initial_data)

    @staticmethod
    def delete_dir(path: Path) -> None:
        path.rmdir()

    @staticmethod
    def delete_multi_dir(list_of_paths: list[Path]) -> None:
        for path in list_of_paths:
            FileManager.delete_dir(path)

    @staticmethod
    def delete_file(path: Path) -> None:
        path.unlink(missing_ok=True)

    @staticmethod
    def delete_multi_file(list_of_paths: list[Path]) -> None:
        for path in list_of_paths:
            FileManager.delete_file(path)


if __name__ == "__main__":
    fm = FileManager(Path("test.json"))
    fm.create_json_file()
    fm.save({"test": "test"})
    print(fm.load())
