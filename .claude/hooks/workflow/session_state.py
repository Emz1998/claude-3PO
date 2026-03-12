"""SessionState — session-scoped wrapper around StateStore.

All hooks use this instead of raw StateStore for session data.
Sessions are stored under state["sessions"][story_id].
"""

import os
from pathlib import Path
from typing import Any, Callable

from workflow.state_store import StateStore
from workflow.config import get as cfg


class SessionState:
    def __init__(self, state_path: Path | str | None = None):
        path = state_path or cfg("paths.workflow_state")
        self._store = StateStore(Path(path))
        self._story_id = os.environ.get("STORY_ID")

    @property
    def story_id(self) -> str | None:
        return self._story_id

    @property
    def store(self) -> StateStore:
        return self._store

    def get_session(self, story_id: str) -> dict | None:
        """Return the session dict for story_id, or None if missing."""
        state = self._store.load()
        sessions = state.get("sessions", {})
        return sessions.get(story_id)

    def get_session_by_id(self, session_id: str) -> dict | None:
        """Return the session dict for session_id, or None if missing."""
        state = self._store.load()
        sessions = state.get("sessions", {})
        return next(
            (
                session
                for session in sessions.values()
                if session.get("session_id") == session_id
            ),
            None,
        )

    def create_session(self, story_id: str, data: dict) -> None:
        """Create or overwrite a session entry under sessions.<story_id>."""

        def _create(state: dict) -> None:
            if "sessions" not in state:
                state["sessions"] = {}
            state["sessions"][story_id] = data

        self._store.update(_create)

    def update_session(self, story_id: str, fn: Callable[[dict], None]) -> None:
        """Apply fn to the session dict for story_id. Raises KeyError if missing."""

        def _update(state: dict) -> None:
            sessions = state.get("sessions", {})
            if story_id not in sessions:
                raise KeyError(f"Session '{story_id}' not found")
            fn(sessions[story_id])

        self._store.update(_update)

    def delete_session(self, story_id: str) -> None:
        """Remove the session for story_id. No-op if missing."""

        def _delete(state: dict) -> None:
            sessions = state.get("sessions", {})
            sessions.pop(story_id, None)

        self._store.update(_delete)

    @staticmethod
    def default_implement_session(story_id: str, session_id: str) -> dict:
        """Return the default session template for an implement workflow."""
        return {
            "session_id": session_id,
            "workflow_type": "implement",
            "story_id": story_id,
            "phase": {
                "current": "pre-coding",
                "previous": None,
                "recent_agent": None,
            },
            "control": {
                "status": "running",
                "hold": False,
                "blocked_until_phase": None,
            },
            "pr": {
                "created": False,
                "number": None,
            },
            "validation": {
                "decision_invoked": False,
                "confidence_score": 0,
                "quality_score": 0,
                "iteration_count": 0,
                "escalate_to_user": False,
            },
            "ci": {
                "status": "pending",
                "iteration_count": 0,
                "escalate_to_user": False,
            },
        }

    @staticmethod
    def default_pr_review_session(pr_number: int, session_id: str) -> dict:
        """Return the default session template for a PR review workflow."""
        return {
            "session_id": session_id,
            "workflow_type": "pr-review",
            "phase": {
                "current": "pr-review",
                "previous": None,
                "recent_agent": None,
            },
            "control": {
                "status": "running",
                "hold": False,
                "blocked_until_phase": None,
            },
            "pr": {
                "created": True,
                "number": pr_number,
            },
            "validation": {
                "decision_invoked": False,
                "confidence_score": 0,
                "quality_score": 0,
                "iteration_count": 0,
                "escalate_to_user": False,
            },
            "ci": {
                "status": "pending",
                "iteration_count": 0,
                "escalate_to_user": False,
            },
        }
