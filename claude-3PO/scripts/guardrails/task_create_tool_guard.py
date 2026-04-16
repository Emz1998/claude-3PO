"""TaskCreateToolGuard — PreToolUse guard for TaskCreate tool.

Implement workflow: validates metadata.parent_task_id and parent_task_title
exist and match a project task in state.
Build workflow: allows (validation happens in TaskCreated hook).
"""

from typing import Literal

from lib.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class TaskCreateToolGuard:
    """Validate TaskCreate tool input at PreToolUse."""

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.workflow_type = state.get("workflow_type", "build")

    def _get_metadata(self) -> dict:
        tool_input = self.hook_input.get("tool_input", {})
        return tool_input.get("metadata") or {}

    def _check_parent_task_id(self, parent_task_id: str | None) -> None:
        if not parent_task_id:
            raise ValueError(
                "TaskCreate in implement workflow requires metadata.parent_task_id. "
                "Set metadata: {parent_task_id: '<project-task-id>', parent_task_title: '<title>'}"
            )

    def _check_parent_task_title(self, parent_task_title: str | None) -> None:
        if not parent_task_title:
            raise ValueError(
                "TaskCreate in implement workflow requires metadata.parent_task_title. "
                "Set metadata: {parent_task_id: '<project-task-id>', parent_task_title: '<title>'}"
            )

    def _check_parent_exists(self, parent_task_id: str) -> None:
        project_tasks = self.state.project_tasks
        matched = any(pt.get("id") == parent_task_id for pt in project_tasks)
        if not matched:
            task_ids = [pt.get("id") for pt in project_tasks]
            raise ValueError(
                f"parent_task_id '{parent_task_id}' not found in project tasks.\n"
                f"Available: {task_ids}"
            )

    def validate(self) -> Decision:
        """Returns ("allow", message) or ("block", reason)."""
        try:
            if self.workflow_type != "implement":
                return "allow", "TaskCreate allowed (build workflow)"

            metadata = self._get_metadata()
            parent_task_id = metadata.get("parent_task_id")
            parent_task_title = metadata.get("parent_task_title")

            self._check_parent_task_id(parent_task_id)
            self._check_parent_task_title(parent_task_title)
            self._check_parent_exists(parent_task_id)

            return "allow", f"TaskCreate allowed (parent: {parent_task_id})"
        except ValueError as e:
            return "block", str(e)
