from typing import Literal


from scripts.claude_hooks.sprint.types import Bucket, SprintState
from scripts.claude_hooks.sprint.sprint_config import SprintConfig


class TaskManager:
    """Task manager for workflow orchestration."""

    def __init__(self, state: SprintState, config: SprintConfig):
        """Initialize the task manager.

        Args:
            story_id: The story id
            task_path: Path to the task.json file
        """
        self._state = state
        self._config = config

    def get_ready_tasks(self, story_id: str | None = None) -> list[str]:
        """Get tasks whose deps are met and aren't already started or done."""
        tasks = self._state.tasks
        if story_id is None:
            story_id = self._state.current_story
        if tasks.get(story_id) is None:
            return []
        exclude = set(tasks[story_id].in_progress) | set(tasks[story_id].completed)

        story = self._config.sprint.find_story(story_id)
        if not story:
            return []

        candidates = story.get_tasks_without_deps()
        for task_id in story.get_tasks_with_deps():
            task = story.find_task(task_id)
            if task and all(
                dep in tasks[story_id].completed for dep in task.depends_on
            ):
                candidates.append(task_id)

        return [t for t in candidates if t not in exclude]

    def get_pending_tasks(self, story_id: str | None = None) -> list[str]:
        """Get tasks not yet ready, in progress, or completed."""
        tasks = self._state.tasks
        if story_id is None:
            story_id = self._state.current_story
        if tasks.get(story_id) is None:
            return []
        exclude = (
            set(tasks[story_id].in_progress)
            | set(tasks[story_id].completed)
            | set(self.get_ready_tasks(story_id))
        )

        story = self._config.sprint.find_story(story_id)
        if not story:
            return []
        return [t for t in story.get_task_ids() if t not in exclude]

    def resolve_tasks(self, story_id: str | None = None) -> None:
        """Resolve the tasks."""
        tasks = self._state.tasks
        if story_id is None:
            story_id = self._state.current_story
        if not story_id:
            return
        if tasks.get(story_id) is None:
            tasks[story_id] = Bucket()
        tasks[story_id].ready = self.get_ready_tasks(story_id)
        tasks[story_id].pending = self.get_pending_tasks(story_id)
        self._state.tasks = tasks

    def mark_task(
        self,
        task_id: str,
        status: Literal["in_progress", "completed"],
        story_id: str | None = None,
    ) -> tuple[bool, str]:
        """Transition a task to the given status."""
        tasks = self._state.tasks
        if story_id is None:
            story_id = self._state.current_story
        if tasks.get(story_id) is None:
            return False, f"Story '{story_id}' not found"
        ready = tasks[story_id].ready
        in_progress = tasks[story_id].in_progress
        completed = tasks[story_id].completed

        if status == "in_progress":
            if task_id in in_progress:
                return False, f"Task '{task_id}' is already in progress"
            if task_id in completed:
                return False, f"Task '{task_id}' is already completed"
            if task_id not in ready:
                return False, f"Task '{task_id}' is not in ready"
            ready.remove(task_id)
            in_progress.append(task_id)
            self._state.tasks = tasks
            return True, f"Task '{task_id}' marked as in progress"

        if task_id not in in_progress:
            return False, f"Task '{task_id}' must be in progress before completing"
        in_progress.remove(task_id)
        completed.append(task_id)
        self._state.tasks = tasks
        self.resolve_tasks(self._state.current_story)
        return True, f"Task '{task_id}' marked as completed"
