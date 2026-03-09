"""StateStore — JSON state with file-locking."""

import json
from pathlib import Path
from typing import Any, Callable
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workflow.lib.file_manager import FileManager


class StateStore:
    def __init__(
        self, state_path: Path | str, default_state: dict[str, Any] | None = None
    ):
        self._fm = FileManager(Path(state_path), lock=True)
        self._fm.create_json_file(default_state)

    def load(self) -> dict[str, Any]:
        return self._fm.load() or {}

    def save(self, state: dict[str, Any] | None = None) -> None:
        self._fm.save(state)

    def update(self, fn: Callable[[dict[str, Any]], None]) -> None:
        self._fm.update(fn)

    def get(self, key: str, default: Any = None) -> Any:
        data = self.load()
        if key not in data and default is not None:
            self.set(key, default)
            return default
        return data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.update(lambda d: d.update({key: value}))

    def reset(self) -> None:
        self._fm.save({})

    def delete(self) -> None:
        self._fm.delete()

    def archive(self, history_path: Path) -> None:
        """Append current state as a JSONL entry to history_path."""
        history_fm = FileManager(history_path, lock=True)
        entry = json.dumps(self.load()) + "\n"
        history_fm.append(entry)

    @staticmethod
    def latest_from_history(history_path: Path) -> dict[str, Any] | None:
        """Return the last archived entry or None."""
        history_fm = FileManager(history_path, lock=True)
        entries = history_fm.load()
        if not entries:
            return None
        return entries[-1] if isinstance(entries, list) else None


if __name__ == "__main__":
    state_store = StateStore(Path("project/test.json"), default_state={"test": "test"})
    print(state_store.load())
