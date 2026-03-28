"""SessionState — session-scoped wrapper around StateStore.

All hooks use this instead of raw StateStore for session data.
Sessions are stored under state["sessions"][story_id].
"""

import os
from pathlib import Path
import sys
from typing import Any, Literal, cast


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from workflow.state_store import StateStore


DEFAULT_STATE_PATH = Path(__file__).resolve().parent / "state.json"


def resolve_path(session_id: str) -> Path:
    return Path(".claude") / "sessions" / f"session_{session_id}" / "state.json"


class SessionState(StateStore):
    def __init__(self, session_id: str | None = None):
        if session_id is None:
            path = DEFAULT_STATE_PATH
        else:
            path = resolve_path(session_id)
        super().__init__(path)

    @property
    def workflow_type(self) -> str:
        return self.get("workflow_type")

    @property
    def workflow_active(self) -> bool:
        return self.get("workflow_active", False)

    @property
    def session_id(self) -> str:
        return self.get("session_id")

    @property
    def story_id(self) -> str:
        return self.get("story_id")

    @property
    def TDD(self) -> bool:
        return self.get("TDD", False)

    @property
    def tool_enforcement(self) -> dict:
        return self.get("tool_enforcement", {})

    @property
    def force_stop(self) -> dict:
        return self.get("force_stop", {})

    @property
    def phases(self) -> dict:
        return self.get("phases", {})

    @property
    def current_phase(self) -> str:
        return self.phases.get("current", "")

    @property
    def phases_completed(self) -> list[str]:
        return self.phases.get("completed", [])

    @property
    def plan_mode(self) -> bool:
        return self.get("plan_mode", {}).get("status", "inactive") == "active"

    @property
    def pr(self) -> dict:
        return self.get("pr", {})

    @property
    def pr_status(self) -> str:
        return self.pr.get("status", "not_created")

    @property
    def pr_number(self) -> int:
        return self.pr.get("number", 0)

    @property
    def ci(self) -> dict:
        return self.get("ci", {})

    @property
    def ci_status(self) -> str:
        return self.ci.get("status", "inactive")

    def files(
        self,
        _type: Literal["plan", "test", "code"] | None = None,
    ) -> dict | list[dict] | None:
        files = self.get("files", {})
        if _type is None:
            return files

        files = files.get(_type, {})
        if not files:
            return None
        return files

    # --------------------------------- Setters ---------------------------------

    def set_workflow_active(self, value: bool) -> None:
        self.set("workflow_active", value)

    def set_workflow_type(self, workflow_type: str) -> None:
        self.set("workflow_type", workflow_type)

    def set_story_id(self, story_id: str) -> None:
        self.set("story_id", story_id)

    def set_session_id(self, session_id: str) -> None:
        self.set("session_id", session_id)

    def set_TDD(self, value: bool) -> None:
        self.set("TDD", value)

    def set_tool_enforcement(self, value: dict) -> None:
        self.set("tool_enforcement", value)

    def set_force_stop(self, value: dict) -> None:
        self.set("force_stop", value)

    def set_phases(self, value: dict) -> None:
        self.set("phases", value)

    def set_pr(self, value: dict) -> None:
        self.set("pr", value)

    def set_ci_status(self, status: str) -> None:
        self.set("ci", {"status": status})

    def set_files(
        self,
        _type: Literal["plan", "test", "code"] | None,
        value: dict | list[dict],
    ) -> None:
        self.set("files", {_type: value})

    # Helpers

    def find_file(
        self,
        _type: Literal["plan", "test", "code"],
        key: str,
        value: Any,
    ) -> dict | None:
        files = cast(list[dict], self.files(_type))
        if files is None:
            return None
        return next((file for file in files if file.get(key) == value), None)

    def get_files(
        self,
        _type: Literal["plan", "test", "code"],
        status: Literal["needs_revision", "needs_refactoring"] | None = None,
        iteration_left: int | None = None,
    ) -> list[dict]:
        files = cast(list[dict], self.files(_type))
        if files is None:
            return []
        if status is not None:
            files = [file for file in files if file.get("status") == status]
        if iteration_left is not None:
            files = [
                file for file in files if file.get("iteration_left") == iteration_left
            ]
        return files

    def initialize(self) -> None:
        default_state = SessionState.get_default_state()
        self.reinitialize(default_state)

    def add_file(self, _type: Literal["plan", "test", "code"], value: dict) -> None:
        if _type == "plan":
            self.set("files", {_type: value})
            return

        current_files = cast(list[dict], self.files("test"))
        if current_files is None:
            current_files = []
        current_files.append(value)
        self.set("files", {_type: current_files})

    # Default states

    @staticmethod
    def get_default_state() -> dict:
        """Return the default session template for an implement workflow."""
        return {
            "workflow_active": False,
            "workflow_type": None,
            "session_id": None,
            "story_id": None,
            "TDD": False,
            "tool_enforcement": {
                "status": "inactive",
                "tools": [],
            },
            "force_stop": {
                "reason": None,
                "status": "inactive",
            },
            "files": {
                "codebase_status_report": {
                    "path": None,
                    "status": "not_reviewed",
                },
                "plan": {
                    "path": None,
                    "status": "not_reviewed",
                },
                "test": [
                    {
                        "path": None,
                        "status": "not_reviewed",
                    }
                ],
                "code": [
                    {
                        "path": None,
                        "status": "not_reviewed",
                    }
                ],
            },
            "phases": {
                "current": "pre-coding",
                "completed": [],
            },
            "plan_mode": {
                "status": "inactive",
            },
            "pr": {"status": "not_created", "number": None},
            "ci": {
                "status": "inactive",
            },
        }

    @staticmethod
    def default_pr_review_session(pr_number: int, session_id: str) -> dict:
        """Return the default session template for a PR review workflow."""
        return {
            "workflow_active": True,
            "session_id": session_id,
            "pr_number": pr_number,
            "workflow_type": "pr-review",
            "fully_blocked": {
                "status": "inactive",
                "reason": None,
                "exception": None,
            },
            "tool_block": {
                "status": "inactive",
                "reason": None,
                "list": None,
            },
            "force_stop": {
                "reason": None,
                "status": "inactive",
            },
            "review": {
                "status": "inactive",
                "decision_invoked": False,
                "confidence_score": 0,
                "quality_score": 0,
                "iteration_count": 0,
                "escalate_to_user": False,
            },
            "ci": {
                "status": "inactive",
            },
        }
