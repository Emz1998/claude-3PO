"""TaskCreatedGuard — Validates task subject and records in state.

Build workflow: matches task_subject against plan ## Tasks bullets.
Implement workflow: matches task_subject against project_tasks titles,
records child task under the parent.
"""

from typing import Literal

from lib.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class TaskCreatedGuard:
    """Validate TaskCreated hook and record task in state."""

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.workflow_type = state.get("workflow_type", "build")

    @staticmethod
    def _match_substring(subject: str, candidates: list[str]) -> str | None:
        """Case-insensitive substring match. Returns matched candidate or None."""
        normalized = subject.strip().lower()
        for c in candidates:
            c_lower = c.strip().lower()
            if normalized == c_lower or c_lower in normalized or normalized in c_lower:
                return c
        return None

    def _check_task_fields(self, subject: str, description: str) -> None:
        if not description or not description.strip():
            raise ValueError("Task must have a non-empty description.")
        if not subject or not subject.strip():
            raise ValueError("Task must have a non-empty subject.")

    def _validate_build_task(self, subject: str) -> str:
        """Match subject against plan tasks and record creation."""
        planned_tasks = self.state.tasks
        if not planned_tasks:
            raise ValueError(
                "No planned tasks found in state. Create a plan with ## Tasks first."
            )

        matched = self._match_substring(subject, planned_tasks)
        if not matched:
            raise ValueError(
                f"Task '{subject}' does not match any planned task.\n"
                f"Planned tasks: {planned_tasks}"
            )

        self.state.add_created_task(matched)
        return f"Build task recorded: {matched}"

    def _validate_implement_task(self, task_id: str, subject: str) -> str:
        """Match subject against project tasks and record child."""
        project_tasks = self.state.project_tasks
        if not project_tasks:
            raise ValueError(
                "No project tasks found in state. "
                "The create-tasks phase must load tasks from the project manager first."
            )

        titles = [pt.get("title", "") for pt in project_tasks]
        matched_title = self._match_substring(subject, titles)
        if not matched_title:
            raise ValueError(
                f"Task '{subject}' does not match any project task.\n"
                f"Project tasks: {titles}"
            )

        for pt in project_tasks:
            if pt.get("title", "").strip().lower() == matched_title.strip().lower():
                self.state.add_subtask(pt["id"], {
                    "task_id": task_id,
                    "subject": subject,
                    "status": "in_progress",
                })
                break

        return f"Implement task recorded under: {matched_title}"

    def validate(self) -> Decision:
        """Returns ("allow", message) or ("block", reason)."""
        try:
            task_id = self.hook_input.get("task_id", "")
            subject = self.hook_input.get("task_subject", "")
            description = self.hook_input.get("task_description", "")

            self._check_task_fields(subject, description)

            if self.workflow_type == "implement":
                message = self._validate_implement_task(task_id, subject)
            else:
                message = self._validate_build_task(subject)

            return "allow", message
        except ValueError as e:
            return "block", str(e)
