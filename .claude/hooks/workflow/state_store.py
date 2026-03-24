"""StateStore — JSON state with file-locking."""

import json
from pathlib import Path
from typing import Any, Callable, Literal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workflow.lib.file_manager import FileManager


class StateStore:
    def __init__(self, state_path: Path, default_state: dict[str, Any] | None = None):
        self._path = state_path
        self._fm = FileManager(self._path, lock=True)

    def load(self) -> dict[str, Any]:
        return self._fm.load_file() or {}

    def save(self, state: dict[str, Any] | None = None) -> None:
        self._fm.save_file(state)

    def update(self, fn: Callable[[dict[str, Any]], None]) -> None:
        self._fm.update_file(fn)

    def get(self, key: str, default: Any = None) -> Any:
        data = self.load()
        return data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.update(lambda d: d.update({key: value}))

    def reset(self, default_state: dict[str, Any] | None = None) -> None:
        self._fm.save_file(default_state or {})

    def reinitialize(self, initial_state: dict[str, Any]) -> None:
        self._fm.save_file(initial_state)

    def delete(self) -> None:
        self._fm.delete_file()

    def archive(self, history_path: Path) -> None:
        """Append current state as a JSONL entry to history_path."""
        history_fm = FileManager(history_path, lock=True)
        entry = json.dumps(self.load()) + "\n"
        history_fm.save_file(entry, mode="a")

    @staticmethod
    def latest_from_history(history_path: Path) -> dict[str, Any] | None:
        """Return the last archived entry or None."""
        history_fm = FileManager(history_path, lock=True)
        entries = history_fm.load_file()
        if not entries:
            return None
        return entries[-1] if isinstance(entries, list) else None
