import json
import os
from pathlib import Path
from typing import Any, Callable
from filelock import FileLock
import sys

_JSON_SUFFIXES = {".json", ".jsonl"}


def append_text(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        print(f"Error appending to file: {e}")
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
    if path.suffix == ".jsonl":
        return load_jsonl(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, TypeError):
        return default if default is not None else set_default(path)
    if path.suffix == ".json":
        if not text.strip():
            return default if default is not None else {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if default is not None:
                write_file(path, default)
                return default
            return {}
    return text


def write_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    content = json.dumps(data, indent=2) if path.suffix == ".json" else str(data)
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def update_file(path: Path, fn: Callable[[Any], None]) -> None:
    data = load_file(path)
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
        self._lock = FileLock(path.with_suffix(".lock")) if lock else None
        self._data: Any | None = None

        if not self._path.exists() and self._path.suffix in _JSON_SUFFIXES:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            if self._path.suffix == ".jsonl":
                self._path.touch()
                self._data = []
            else:
                self._data = {}
                write_file(self._path, self._data)
        self.load(set_default(self._path))

    def load(self, default: Any | None = None) -> Any | None:
        if self._lock is None:
            self._data = load_file(self._path, default)
            return self._data

        with self._lock:
            self._data = load_file(self._path, default)
            return self._data

    def save(self, data: Any | None = None) -> None:
        if data is None:
            data = self._data
        if self._lock is None:
            write_file(self._path, data)
            return
        with self._lock:
            write_file(self._path, data)

    def update(self, fn: Callable[[Any], None]) -> None:
        """Atomic read-modify-write."""
        if self._lock is None:
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
        if self._lock is None:
            append_text(path, data)
            return
        with self._lock:
            append_text(path, data)
