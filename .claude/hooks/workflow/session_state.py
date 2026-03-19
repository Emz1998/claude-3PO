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
from workflow.config import get as cfg

MAX_ITERATIONS = cfg("validation.iteration_loop", 3)


def resolve_path(session_id: str) -> Path:
    return Path(".claude") / "sessions" / f"session_{session_id}" / "state.json"


class SessionState(StateStore):
    def __init__(self, session_id: str):
        path = resolve_path(session_id)
        super().__init__(path)

    @property
    def story_id(self) -> str:
        return self.get("story_id")

    @property
    def commit_status(self) -> Literal["pending", "committed", "inactive"]:
        return self.get("commit", {}).get("status", "inactive")

    @property
    def current_phase(self) -> str:
        return self.get("phase", {}).get("current")

    @property
    def previous_phase(self) -> str | None:
        return self.get("phase", {}).get("previous")

    @property
    def previous_agent(self) -> str | None:
        return self.get("agent", {}).get("previous")

    @property
    def workflow_active(self) -> bool:
        return self.get("workflow_active", False)

    @property
    def permission_mode(self) -> str:
        return self.get("permission_mode", "default")

    @property
    def plan_mode(self) -> bool:
        return self.get("plan_mode", {}).get("status", "inactive") == "active"

    @property
    def _tool_block(self) -> dict:
        return self.get("tool_block", {})

    @property
    def TDD(self) -> bool:
        return self.get("TDD", False)

    @property
    def _tool_enforcement(self) -> dict:
        return self.get("tool_enforcement", {})

    @property
    def enforced_tools(self) -> list[tuple[str, str | None]]:
        return [
            (tool["matcher"], tool["name"])
            for tool in self._tool_enforcement.get("tools", [])
        ]

    @property
    def tool_enforcement_status(self) -> str:
        return self._tool_enforcement.get("status", "inactive")

    def set_phase(
        self, query: Literal["current", "previous", "recent_agent"], value: str
    ) -> None:
        self.update(lambda d: d.get("phase", {}).update({query: value}))

    def set_pr(self, query: Literal["status", "number"], value: str) -> None:
        self.update(lambda d: d.get("pr", {}).update({query: value}))

    def set_story_id(self, story_id: str) -> None:
        self.set("story_id", story_id)

    def delete(self) -> None:
        self.delete()

    def set_session_id(self, session_id: str) -> None:
        self.set("session_id", session_id)

    def set_workflow_active(self, workflow_active: bool) -> None:
        self.set("workflow_active", workflow_active)

    def set_workflow_type(self, workflow_type: str) -> None:
        self.set("workflow_type", workflow_type)

    def set_review_by_key(self, key: str, val: Any) -> None:
        review_data = self.get("review", "")
        new_review_data = {**review_data, key: val}
        self.set("review", new_review_data)

    def set_review(self, review_data: dict) -> None:
        _review_data = self.get("review", "")
        new_review_data = {**_review_data, **review_data}
        self.set("review", new_review_data)

    def set_agent(self, query: Literal["current", "previous"], value: str) -> None:
        self.update(lambda d: d.get("agent", {}).update({query: value}))

    def set_ci(
        self, query: Literal["status", "failure_count"], value: str | int
    ) -> None:
        self.update(lambda d: d.get("ci", {}).update({query: value}))

    def set_commit(self, status: Literal["pending", "committed", "inactive"]) -> None:
        self.set("commit", {"status": status})

    def set_full_block(
        self,
        status: Literal["active", "inactive"],
        exception: list[dict[str, Any]] | None = None,
    ) -> None:
        self.set(
            "full_block",
            {"status": status, "exception": exception},
        )

    def set_force_stop(self, reason: str) -> None:
        self.set("force_stop", {"reason": reason, "status": "active"})

    def set_enforced_tools(self, tool_data: list[dict[str, str | None]]) -> None:
        self.update(
            lambda d: d.get("tool_enforcement", {}).update({"tools": tool_data})
        )

    def set_tool_enforcement_status(
        self, status: Literal["active", "inactive", "bypass"]
    ) -> None:
        self.update(lambda d: d.get("tool_enforcement", {}).update({"status": status}))

    def update_full_block(
        self, key: Literal["status", "exceptions"], value: Any
    ) -> None:
        self.update(lambda d: d.get("full_block", {}).update({key: value}))

    def update_block_list(
        self,
        list_type: Literal["full_block", "tool_block"],
        value: Any,
    ) -> None:
        match list_type:
            case "full_block":
                self.update(
                    lambda d: d.get("full_block", {}).update({"exceptions": value})
                )
            case "tool_block":
                self.update(lambda d: d.get("tool_block", {}).update({"list": value}))

    # Helpers

    def enforce_tool(self, tool_name: str, tool_value: str | None) -> None:
        current_tools = self.get("tool_enforcement", {}).get("tools", [])

        current_tools.append({"matcher": tool_name, "name": tool_value})

        self.set_enforced_tools(current_tools)

    def remove_enforced_tool(self, tool_name: str, tool_value: str | None) -> None:
        current_tools = self.get("tool_enforcement", {}).get("tools", [])
        normalized_tool = {"matcher": tool_name, "name": tool_value}
        if normalized_tool not in current_tools:
            return
        current_tools.remove(normalized_tool)
        self.set_enforced_tools(current_tools)

    def check_exist_in_list(
        self,
        list_type: Literal["full_block", "tool_block"],
        raw_tool_name: str,
        raw_tool_value: Any,
    ) -> tuple[bool, str, int]:

        match list_type:
            case "full_block":
                list_of_items = cast(
                    list[dict[str, Any]], self.full_block("exceptions")
                )

            case "tool_block":
                list_of_items = cast(list[dict[str, Any]], self.tool_block("list"))

        if not list_of_items:
            return (
                False,
                f"{list_type} list is empty",
                -1,
            )

        for index, item in enumerate(list_of_items):
            if (
                item.get("tool_name") == raw_tool_name
                and item.get("tool_value") == raw_tool_value
            ):
                reason = item.get("reason", "No reason provided")
                return (
                    True,
                    reason,
                    index,
                )
        return (
            False,
            "Tool not found in list",
            -1,
        )

    def release(
        self,
        list_type: Literal["full_block", "tool_block"],
        raw_tool_name: str,
        raw_tool_value: Any,
    ) -> None:
        match list_type:
            case "full_block":
                status = self.full_block("status")
                list_of_items = self.full_block("exceptions")
            case "tool_block":
                status = self.tool_block("status")
                list_of_items = self.tool_block("list")

        if status == "inactive":
            return

        if not (raw_tool_name or raw_tool_value):
            raise ValueError("raw_tool_name and raw_tool_value must be provided")

        if not raw_tool_name:
            raise ValueError("raw_tool_name must be provided")

        if not raw_tool_value:
            raise ValueError("raw_tool_value must be provided")

        if not isinstance(list_of_items, list):
            raise TypeError("exceptions must be a list")

        in_list, _, index = self.check_exist_in_list(
            list_type, raw_tool_name, raw_tool_value
        )

        if not in_list:
            return

        if list_type == "full_block":
            list_of_items.pop(index)
            self.update_block_list("full_block", list_of_items)
        elif list_type == "tool_block":
            list_of_items.pop(index)
            self.update_block_list("tool_block", list_of_items)

    def tool_block(
        self, query: Literal["status", "reason", "list"]
    ) -> str | list[dict[str, Any]]:
        match query:
            case "status":
                return self._tool_block.get("status", "inactive")
            case "reason":
                return self._tool_block.get("reason", "Only block is active.")
            case "list":
                return self._tool_block.get("list", [])

    @property
    def _full_block(self) -> dict:
        return self.get("full_block", {})

    def full_block(
        self, query: Literal["status", "exceptions"]
    ) -> str | list[dict[str, Any]]:
        match query:
            case "status":
                return self._full_block.get("status", "inactive")
            case "exceptions":
                return self._full_block.get("exceptions", [])

    def append_to_block_list(
        self,
        tool_name: str,
        tool_value: Any,
        reason: str,
        block_list: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        block_list.append(
            {
                "tool_name": tool_name,
                "tool_value": tool_value,
                "reason": reason,
            }
        )
        return block_list

    def add(
        self,
        list_type: Literal["full_block", "tool_block"],
        tool_name: str,
        tool_value: Any,
        reason: str,
    ) -> None:

        in_list, _, _ = self.check_exist_in_list(list_type, tool_name, tool_value)
        if in_list:
            return

        if list_type == "full_block":
            list_of_items = cast(list[dict[str, Any]], self.full_block("exceptions"))
        else:
            list_of_items = cast(list[dict[str, Any]], self.tool_block("list"))

        new_list = self.append_to_block_list(
            tool_name, tool_value, reason, list_of_items
        )
        self.update_block_list(list_type, new_list)

    def cleanup_review(self) -> None:
        default_review_state = SessionState.default_review_state()
        self.set_review(default_review_state)

    def initialize(self) -> None:
        default_state = SessionState.default_state()
        self.reset(default_state)

    # Default states

    @staticmethod
    def default_fully_blocked_state() -> dict:
        return {
            "status": "inactive",
            "reason": None,
            "exception": None,
        }

    @staticmethod
    def default_review_state() -> dict:
        return {
            "status": "inactive",
            "phase": None,
            "report_written": False,
            "confidence_score": 0,
            "quality_score": 0,
            "iteration_left": MAX_ITERATIONS,
        }

    @staticmethod
    def default_tool_block_state() -> dict:
        return {
            "status": "active",
            "reason": None,
            "list": [["command", "gh pr create"]],
        }

    @staticmethod
    def default_state() -> dict:
        """Return the default session template for an implement workflow."""
        return {
            "workflow_active": False,
            "workflow_type": None,
            "session_id": None,
            "story_id": None,
            "TDD": False,
            "fully_blocked": {"status": "inactive", "reason": None, "exception": None},
            "tool_block": SessionState.default_tool_block_state(),
            "force_stop": {
                "reason": None,
                "status": "inactive",
            },
            "phase": {
                "current": "pre-coding",
                "previous": None,
            },
            "skill": {"current": None, "previous": None},
            "agent": {"current": None, "previous": None},
            "plan_mode": {
                "status": "inactive",
            },
            "written_files": {"recent": None},
            "edited_files": {"recent": None},
            "commands": {"recent": None},
            "pr": {"status": "not_created", "number": None},
            "ci": {
                "status": "inactive",
            },
            "review": SessionState.default_review_state(),
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
