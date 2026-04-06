"""FileManager with file locking for JSON/JSONL files."""

import json
import os
from pathlib import Path
from typing import Any, Callable, cast, Literal
from filelock import FileLock, BaseFileLock
import sys

JSON_SUFFIXES = {".json", ".jsonl"}


def create_file(path: Path, default: Any | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".json":
        default = default or {}
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return
    path.touch()


def load_file(path: Path) -> Any:
    if not path.exists():
        create_file(path)
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return {}

        return json.loads(content)

    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupt JSON in {path}: {e}") from e


def save_file(data: Any, mode: Literal["w", "a", "x"], path: Path) -> None:
    try:
        with path.open(mode, encoding="utf-8") as f:
            if path.suffix in JSON_SUFFIXES:
                json.dump(data, f, indent=2)
            else:
                f.write(data)
    except TypeError as e:
        raise TypeError(f"Invalid data type: {type(data)} \nError: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Error saving file: {path} \nError: {e}") from e


def update_file(path: Path, fn: Callable[[Any], None]) -> None:
    data = load_file(path)
    fn(data)
    save_file(data, "w", path)


class FileManager:
    def __init__(self, path: Path, lock: bool = True):
        self._path = path
        self._lock = FileLock(path.with_suffix(".lock")) if lock else None

    def create_file(self, default: Any | None = None) -> None:
        create_file(self._path, default)

    def load_file(self) -> Any:
        if self._lock is None:
            return load_file(self._path)
        with self._lock:
            return load_file(self._path)

    def save_file(self, data: Any, mode: Literal["w", "a", "x"] = "w") -> None:
        save_file(data, mode, self._path)

    def update_file(self, fn: Callable[[Any], None]) -> None:
        data = load_file(self._path)
        fn(data)
        save_file(data, "w", self._path)

    def delete_file(self) -> None:
        self._path.unlink()
