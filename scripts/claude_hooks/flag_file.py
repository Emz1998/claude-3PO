"""Generic flag file manager — file existence = flag is active."""

import json
from pathlib import Path
from typing import Any
from filelock import FileLock

FLAG_DIR = Path.cwd() / "project" / "tmp"


class FlagFile:
    def __init__(self, name: str):
        self._path = FLAG_DIR / f"{name}.json"
        self._lock = FileLock(self._path.with_suffix(".lock"))

    @property
    def path(self) -> Path:
        return self._path

    def exists(self) -> bool:
        return self._path.exists()

    def read(self) -> dict | None:
        if not self._path.exists():
            return None
        with self._lock:
            text = self._path.read_text(encoding="utf-8")
            return json.loads(text) if text.strip() else None

    def write(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def update(self, key: str, value: Any) -> dict:
        state = self.read() or {}
        state[key] = value
        self.write(state)
        return state

    def append_to(self, key: str, value: str) -> dict:
        """Append value to a list field, creating it if needed."""
        state = self.read() or {}
        items = state.get(key, [])
        if value not in items:
            items.append(value)
        state[key] = items
        self.write(state)
        return state

    def remove_from(self, key: str, value: str) -> dict:
        """Remove value from a list field. Returns updated state."""
        state = self.read() or {}
        items = state.get(key, [])
        if value in items:
            items.remove(value)
        state[key] = items
        self.write(state)
        return state

    def remove(self) -> None:
        """Delete flag file and its lock."""
        if self._path.exists():
            self._path.unlink()
        lock = self._path.with_suffix(".lock")
        if lock.exists():
            lock.unlink()
