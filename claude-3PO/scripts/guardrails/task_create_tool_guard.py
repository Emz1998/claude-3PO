"""TaskCreateToolGuard — PreToolUse guard for the TaskCreate tool.

Behaviour depends on workflow type:

- **implement** — requires ``metadata.parent_task_id`` and
  ``metadata.parent_task_title`` and confirms the parent ID matches a project
  task already loaded into state.
- **build** — always allows; the real validation runs later in the
  ``TaskCreated`` Stop-hook (see :class:`TaskCreatedGuard`).
"""

from typing import Literal

from lib.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class TaskCreateToolGuard:
    """Validate the input of a TaskCreate tool call at PreToolUse.

    In the **implement** workflow, this guard makes sure the new task is wired
    to a real project-manager task — both metadata fields are present *and*
    the parent ID is one of the loaded project tasks. In the **build**
    workflow, the guard is a no-op (validation happens at TaskCreated).

    Example:
        >>> guard = TaskCreateToolGuard(hook_input, config, state)  # doctest: +SKIP
        >>> decision, message = guard.validate()  # doctest: +SKIP
    """

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        """
        Cache the hook payload, config, state, and the workflow type.

        Args:
            hook_input (dict): Raw PreToolUse hook payload.
            config (Config): Workflow configuration.
            state (StateStore): Mutable workflow state snapshot.

        Example:
            >>> guard = TaskCreateToolGuard(hook_input, config, state)  # doctest: +SKIP
            >>> guard.workflow_type  # doctest: +SKIP
            'implement'
        """
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.workflow_type = state.get("workflow_type", "build")

    def _get_metadata(self) -> dict:
        """Return the ``metadata`` dict from the tool input (empty when absent).

        Example:
            >>> metadata = guard._get_metadata()  # doctest: +SKIP
        """
        tool_input = self.hook_input.get("tool_input", {})
        return tool_input.get("metadata") or {}

    def _check_parent_task_id(self, parent_task_id: str | None) -> None:
        """
        Require a non-empty ``metadata.parent_task_id``.

        Args:
            parent_task_id (str | None): Value from the metadata dict.

        Raises:
            ValueError: If missing or empty.

        Example:
            >>> # Raises ValueError when parent_task_id is missing:
            >>> guard._check_parent_task_id(None)  # doctest: +SKIP
        """
        if not parent_task_id:
            raise ValueError(
                "TaskCreate in implement workflow requires metadata.parent_task_id. "
                "Set metadata: {parent_task_id: '<project-task-id>', parent_task_title: '<title>'}"
            )

    def _check_parent_task_title(self, parent_task_title: str | None) -> None:
        """
        Require a non-empty ``metadata.parent_task_title``.

        Args:
            parent_task_title (str | None): Value from the metadata dict.

        Raises:
            ValueError: If missing or empty.

        Example:
            >>> # Raises ValueError when parent_task_title is missing:
            >>> guard._check_parent_task_title(None)  # doctest: +SKIP
        """
        if not parent_task_title:
            raise ValueError(
                "TaskCreate in implement workflow requires metadata.parent_task_title. "
                "Set metadata: {parent_task_id: '<project-task-id>', parent_task_title: '<title>'}"
            )

    def _check_parent_exists(self, parent_task_id: str) -> None:
        """
        Require the parent ID to match a known project task.

        Args:
            parent_task_id (str): Already-validated non-empty parent ID.

        Raises:
            ValueError: If no project task in state has that ID.

        Example:
            >>> # Raises ValueError when the parent ID is unknown:
            >>> guard._check_parent_exists("missing-id")  # doctest: +SKIP
        """
        project_tasks = self.state.implement.project_tasks
        matched = any(pt.get("id") == parent_task_id for pt in project_tasks)
        if not matched:
            task_ids = [pt.get("id") for pt in project_tasks]
            raise ValueError(
                f"parent_task_id '{parent_task_id}' not found in project tasks.\n"
                f"Available: {task_ids}"
            )

    def validate(self) -> Decision:
        """
        Validate the TaskCreate input.

        Returns:
            Decision: ``("allow", message)`` if the workflow is build, or if the
            implement-workflow metadata is well-formed and the parent exists.
            Otherwise ``("block", reason)``.

        Example:
            >>> decision, message = guard.validate()  # doctest: +SKIP
            >>> decision  # doctest: +SKIP
            'allow'
        """
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
