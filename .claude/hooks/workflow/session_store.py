"""SessionStore — JSONL-backed session-scoped state store.

Each line in the JSONL file is one session's state, keyed by session_id.
Provides the same public API as StateStore (load, save, update, get, set,
reset, reinitialize, delete) but operates on a single session's entry.
"""

import json
from pathlib import Path
from typing import Any, Callable

from filelock import FileLock

from workflow.config import DEFAULT_STATE_JSONL_PATH


class SessionStore:
    def __init__(
        self,
        session_id: str,
        jsonl_path: Path = DEFAULT_STATE_JSONL_PATH,
    ):
        self._session_id = session_id
        self._path = jsonl_path
        self._lock = FileLock(str(jsonl_path) + ".lock")

    # -------------------------------------------------------------------------
    # Internal JSONL helpers
    # -------------------------------------------------------------------------

    def _read_all(self) -> dict[str, dict[str, Any]]:
        """Read JSONL, return {session_id: state_dict}."""
        if not self._path.exists():
            return {}
        sessions: dict[str, dict[str, Any]] = {}
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                sid = entry.get("session_id")
                if sid:
                    sessions[sid] = entry
            except json.JSONDecodeError:
                continue  # skip corrupt lines
        return sessions

    def _write_all(self, sessions: dict[str, dict[str, Any]]) -> None:
        """Write all sessions back as JSONL (one line per session)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for sid in sorted(sessions):
            entry = sessions[sid]
            # Ensure session_id is the first key in output
            ordered = {"session_id": sid}
            ordered.update({k: v for k, v in entry.items() if k != "session_id"})
            lines.append(json.dumps(ordered, separators=(",", ":")))
        self._path.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")

    # -------------------------------------------------------------------------
    # Public API (matches StateStore)
    # -------------------------------------------------------------------------

    def load(self) -> dict[str, Any]:
        with self._lock:
            sessions = self._read_all()
            return sessions.get(self._session_id, {})

    def save(self, state: dict[str, Any]) -> None:
        state["session_id"] = self._session_id
        with self._lock:
            sessions = self._read_all()
            sessions[self._session_id] = state
            self._write_all(sessions)

    def update(self, fn: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            sessions = self._read_all()
            entry = sessions.get(self._session_id, {})
            entry["session_id"] = self._session_id
            fn(entry)
            sessions[self._session_id] = entry
            self._write_all(sessions)

    def get(self, key: str, default: Any = None) -> Any:
        return self.load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.update(lambda d: d.update({key: value}))

    def reset(self, default_state: dict[str, Any] | None = None) -> None:
        state = default_state or {}
        state["session_id"] = self._session_id
        with self._lock:
            sessions = self._read_all()
            sessions[self._session_id] = state
            self._write_all(sessions)

    def reinitialize(self, initial_state: dict[str, Any]) -> None:
        initial_state["session_id"] = self._session_id
        with self._lock:
            sessions = self._read_all()
            sessions[self._session_id] = initial_state
            self._write_all(sessions)

    def delete(self) -> None:
        with self._lock:
            sessions = self._read_all()
            sessions.pop(self._session_id, None)
            self._write_all(sessions)

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    @classmethod
    def cleanup_inactive(cls, jsonl_path: Path = DEFAULT_STATE_JSONL_PATH) -> int:
        """Remove sessions where workflow_active is False. Returns count removed."""
        lock = FileLock(str(jsonl_path) + ".lock")
        with lock:
            store = cls.__new__(cls)
            store._path = jsonl_path
            store._lock = lock
            sessions = store._read_all()
            before = len(sessions)
            sessions = {
                sid: state
                for sid, state in sessions.items()
                if state.get("workflow_active", False)
            }
            store._write_all(sessions)
            return before - len(sessions)
