#!/usr/bin/env python3
"""Recorder for hook events."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import StateManager  # type: ignore

PHASES = ["explore", "plan", "code", "push"]

STATE_PATH = Path(".claude/hooks/state.json")


class HookState:

    def __init__(
        self,
        state_path: Path = STATE_PATH,
    ):
        self._state_manager = StateManager(state_path)
        self._state_path = state_path

    @property
    def state_manager(self) -> StateManager:
        """Get the state manager."""
        return self._state_manager

    def initialize(self, state: dict[str, Any] | None = None) -> None:
        """Initialize the hook manager.

        Args:
            state: State to initialize the hook manager with
        """
        if state is None:
            state = {
                "current_session_id": None,
                "recent": {
                    "session_id": None,
                    "tool_used": None,
                    "file_written": None,
                    "file_edited": None,
                    "file_read": None,
                    "command_executed": None,
                    "skill_used": None,
                    "subagent_used": None,
                },
                "full_history": {
                    "session_ids": [],
                    "tool_used": [],
                    "file_written": [],
                    "file_edited": [],
                    "file_read": [],
                    "command_executed": [],
                    "skill_used": [],
                    "subagent_used": [],
                },
            }

        self._state_manager.initialize(state)

    # ----------------------------------------
    ## Getters and setters

    def get_current_session_id(self) -> str | None:
        """Get current session id in state.json."""
        session_id = self._state_manager.get("current_session_id")
        if session_id is None:
            print("No current session id found")
            return None
        return session_id

    def set_current_session_id(self, session_id: str) -> bool:
        """Set current session id in state.json."""
        self._state_manager.set("current_session_id", session_id)
        return True

    def get_recent(self, key: str) -> Any | None:
        """Get recent data from state.json."""
        recent = self._state_manager.get("recent")
        if recent is None:
            print("No recent found")
            return None
        return recent.get(key, None)

    def set_recent(self, key: str, value: Any) -> bool:
        """Set recent data in state.json."""
        recent = self._state_manager.get("recent")
        if recent is None:
            print("No recent found")
            return False

        if value == recent.get(key, None):
            return True

        recent[key] = value
        self._state_manager.set("recent", recent)
        return True

    def get_full_history(self, key: str) -> list[Any]:
        """Get full history data from state.json."""
        full_history = self._state_manager.get("full_history")
        if full_history is None:
            print("No full history found")
            return []
        return full_history.get(key, [])

    def set_full_history(self, key: str, value: Any) -> bool:
        """Set full history data in state.json."""
        full_history = self._state_manager.get("full_history")

        if full_history is None:
            print("No full history found")
            return False

        if value in full_history.get(key, []):
            return True

        full_history[key] = [*full_history.get(key, []), value]
        self._state_manager.set("full_history", full_history)
        return True

    def record(self, key: str, value: Any) -> bool:
        """Record an event in state.json."""
        self.set_recent(key, value)
        self.set_full_history(key, value)
        return True
