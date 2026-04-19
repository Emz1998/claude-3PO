"""TaskCreatedGuard — validates task subject at TaskCreated (pure validator).

Per-workflow behaviour:

- **build** — fuzzy-matches ``task_subject`` against the plan's
  ``## Tasks`` bullet list.
- **implement** — fuzzy-matches ``task_subject`` against the titles of
  ``project_tasks`` already loaded from the project manager.

This guard never mutates state. After Allow, dispatchers read the matched
data from these instance attributes:

- ``matched_build_subject`` — set in build workflow with the plan-task string
  that matched.
- ``matched_implement_parent_id`` — set in implement workflow with the parent
  project-task ID.
- ``matched_implement_payload`` — set in implement workflow with the dict
  that should be appended as a child of the parent project task.
"""

from typing import Literal

from lib.extractors import match_substring
from lib.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class TaskCreatedGuard:
    """Validate a TaskCreated hook event. **Pure — never mutates state.**

    On Allow, the matched data is exposed via:

    - ``matched_build_subject`` (build workflow): the plan-task string that
      matched ``task_subject`` (case/substring-insensitive).
    - ``matched_implement_parent_id`` (implement workflow): ID of the project
      task that owns the new task.
    - ``matched_implement_payload`` (implement workflow): payload dict that
      dispatchers should append as a child of the parent project task.

    Example:
        >>> guard = TaskCreatedGuard(hook_input, config, state)  # doctest: +SKIP
        >>> decision, message = guard.validate()  # doctest: +SKIP
    """

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        """
        Cache hook payload and dependencies; reset dispatcher-facing attrs.

        Args:
            hook_input (dict): Raw TaskCreated hook payload.
            config (Config): Workflow configuration.
            state (StateStore): Mutable workflow state snapshot — read only.

        Example:
            >>> guard = TaskCreatedGuard(hook_input, config, state)  # doctest: +SKIP
            >>> guard.matched_build_subject is None  # doctest: +SKIP
            True
        """
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.workflow_type = state.get("workflow_type", "build")
        # Set on Allow so dispatchers can apply side effects.
        self.matched_build_subject: str | None = None
        self.matched_implement_parent_id: str | None = None
        self.matched_implement_payload: dict | None = None

    def check_task_fields(self, subject: str, description: str) -> None:
        """
        Reject tasks lacking either a subject or description.

        Args:
            subject (str): Task subject string.
            description (str): Task description string.

        Raises:
            ValueError: If either field is empty/whitespace-only.

        Example:
            >>> # Raises ValueError when description is empty:
            >>> guard.check_task_fields("Add login", "")  # doctest: +SKIP
        """
        if not description or not description.strip():
            raise ValueError("Task must have a non-empty description.")
        if not subject or not subject.strip():
            raise ValueError("Task must have a non-empty subject.")

    def validate_build_task(self, subject: str) -> str:
        """
        Match a build-workflow subject against the plan's ``## Tasks`` bullets.

        On success, sets ``self.matched_build_subject`` so the dispatcher can
        record progress against the plan task.

        Args:
            subject (str): Task subject from the hook payload.

        Returns:
            str: Success message naming the matched plan task.

        Raises:
            ValueError: If no planned tasks exist or none match the subject.

        Example:
            >>> message = guard.validate_build_task("Add login")  # doctest: +SKIP

        SideEffect:
            Sets ``self.matched_build_subject`` on match.
        """
        planned_tasks = self.state.tasks
        if not planned_tasks:
            raise ValueError(
                "No planned tasks found in state. Create a plan with ## Tasks first."
            )
        matched = match_substring(subject, planned_tasks)
        if not matched:
            raise ValueError(
                f"Task '{subject}' does not match any planned task.\n"
                f"Planned tasks: {planned_tasks}"
            )
        self.matched_build_subject = matched
        return f"Build task recorded: {matched}"

    def validate_implement_task(self, task_id: str, subject: str) -> str:
        """
        Match an implement-workflow subject against project task titles.

        On success, calls :meth:`set_implement_match` to populate the
        dispatcher-facing ``matched_implement_*`` attrs.

        Args:
            task_id (str): Task ID assigned by Claude Code.
            subject (str): Task subject from the hook payload.

        Returns:
            str: Success message naming the matched parent project task.

        Raises:
            ValueError: If project_tasks is empty or no title matches.

        Example:
            >>> message = guard.validate_implement_task("task-1", "Add login")  # doctest: +SKIP

        SideEffect:
            Sets ``self.matched_implement_parent_id`` and
            ``self.matched_implement_payload`` on match.
        """
        project_tasks = self.state.implement.project_tasks
        if not project_tasks:
            raise ValueError(
                "No project tasks found in state. "
                "The create-tasks phase must load tasks from the project manager first."
            )
        titles = [pt.get("title", "") for pt in project_tasks]
        matched_title = match_substring(subject, titles)
        if not matched_title:
            raise ValueError(
                f"Task '{subject}' does not match any project task.\n"
                f"Project tasks: {titles}"
            )
        self.set_implement_match(project_tasks, matched_title, task_id, subject)
        return f"Implement task recorded under: {matched_title}"

    def set_implement_match(
        self, project_tasks: list[dict], matched_title: str, task_id: str, subject: str
    ) -> None:
        """
        Locate the project task by title and stash the parent-id + child payload.

        Args:
            project_tasks (list[dict]): Loaded project tasks.
            matched_title (str): Title returned by :func:`lib.extractors.match_substring`.
            task_id (str): Claude-assigned task ID for the new child.
            subject (str): Subject of the new child task.

        Example:
            >>> guard.set_implement_match(project_tasks, "Add login flow", "t-1", "Add login")  # doctest: +SKIP

        SideEffect:
            Sets ``self.matched_implement_parent_id`` and
            ``self.matched_implement_payload`` to the matched row's data.
        """
        # Case/whitespace-insensitive lookup mirrors the matcher's normalization
        # so we identify the same row the matcher picked.
        for pt in project_tasks:
            if pt.get("title", "").strip().lower() == matched_title.strip().lower():
                self.matched_implement_parent_id = pt["id"]
                self.matched_implement_payload = {
                    "task_id": task_id,
                    "subject": subject,
                    "status": "in_progress",
                }
                return

    def validate(self) -> Decision:
        """
        Validate the TaskCreated event and return an allow/block decision.

        On Allow the dispatcher should consume the appropriate
        ``matched_*`` attribute(s) to apply state changes via Recorder.

        Returns:
            Decision: ``("allow", message)`` if the subject matches a known
            task, otherwise ``("block", reason)``.

        Example:
            >>> decision, message = guard.validate()  # doctest: +SKIP
            >>> decision  # doctest: +SKIP
            'allow'
        """
        try:
            task_id = self.hook_input.get("task_id", "")
            subject = self.hook_input.get("task_subject", "")
            description = self.hook_input.get("task_description", "")

            self.check_task_fields(subject, description)

            if self.workflow_type == "implement":
                message = self.validate_implement_task(task_id, subject)
            else:
                message = self.validate_build_task(subject)

            return "allow", message
        except ValueError as e:
            return "block", str(e)
