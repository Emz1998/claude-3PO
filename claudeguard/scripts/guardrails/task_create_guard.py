"""task_create_guard.py — PreToolUse guard for TaskCreate tool.

Implement workflow: validates metadata.parent_task_id and parent_task_title
exist and match a project task in state.
Build workflow: allows (validation happens in TaskCreated hook).
"""

from typing import Literal

from utils.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


def handle(hook_input: dict, config: Config, state: StateStore) -> Decision:
    try:
        workflow_type = state.get("workflow_type", "build")

        if workflow_type != "implement":
            return "allow", "TaskCreate allowed (build workflow)"

        tool_input = hook_input.get("tool_input", {})
        metadata = tool_input.get("metadata") or {}

        parent_task_id = metadata.get("parent_task_id")
        parent_task_title = metadata.get("parent_task_title")

        if not parent_task_id:
            return "block", (
                "TaskCreate in implement workflow requires metadata.parent_task_id. "
                "Set metadata: {parent_task_id: '<project-task-id>', parent_task_title: '<title>'}"
            )

        if not parent_task_title:
            return "block", (
                "TaskCreate in implement workflow requires metadata.parent_task_title. "
                "Set metadata: {parent_task_id: '<project-task-id>', parent_task_title: '<title>'}"
            )

        # Validate parent_task_id exists in project_tasks
        project_tasks = state.project_tasks
        matched = any(pt.get("id") == parent_task_id for pt in project_tasks)

        if not matched:
            task_ids = [pt.get("id") for pt in project_tasks]
            return "block", (
                f"parent_task_id '{parent_task_id}' not found in project tasks.\n"
                f"Available: {task_ids}"
            )

        return "allow", f"TaskCreate allowed (parent: {parent_task_id})"

    except ValueError as e:
        return "block", str(e)
