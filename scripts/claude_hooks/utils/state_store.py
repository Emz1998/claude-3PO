from pathlib import Path
from typing import Any, Callable

from scripts.claude_hooks.utils.file_manager import FileManager


class StateStore:
    def __init__(self, state_path: Path, default_state: dict[str, Any] | None = None):
        self._fm = FileManager(state_path, lock=True)
        if default_state and self._fm._data == {}:
            self._fm.save(default_state)

    def load(self) -> dict[str, Any]:
        return self._fm.load() or {}

    def save(self, state: dict[str, Any] | None = None) -> None:
        self._fm.save(state)

    def update(self, fn: Callable[[dict[str, Any]], None]) -> None:
        self._fm.update(fn)

    def get(self, key: str, default: Any = None) -> Any:
        data = self._fm._data
        if data is None:
            data = self.load()
        return data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._fm.update(lambda s: s.__setitem__(key, value))

    def reset(self) -> None:
        self._fm.save({})
