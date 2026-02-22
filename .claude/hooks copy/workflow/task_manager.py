#!/usr/bin/env python3
"""Unified state manager for workflow orchestration.

Provides a clean API for workflow state operations, wrapping state.json.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Literal
from filelock import FileLock


sys.path.insert(0, str(Path(__file__).parent))
from sprint_config import SprintConfig  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
STATE_PATH = PROJECT_ROOT / "project/sprints/SPRINT-001/tasks/tasks-status.json"
STATE_LOCK = FileLock(STATE_PATH.with_suffix(".lock"))


class TaskManager:
    """Sprint manager for workflow orchestration."""

    def __init__(self, state_path: Path = STATE_PATH):
        """Initialize the state manager.

        Args:
            state_path: Path to the state.json file
        """
        self._config = SprintConfig()
        self._state_path = state_path
        self._state: dict[str, Any] | None = None

    # ----------------------------------------
    ## Load, save, and persist methods

    def load(self) -> dict[str, Any]:
        """Load state from file.

        Returns:
            State dictionary
        """
        with STATE_LOCK:
            state: dict[str, Any] = {}
            if self._state_path.exists():
                try:
                    state = json.loads(self._state_path.read_text())
                except json.JSONDecodeError:
                    self.initialize()
                    state = json.loads(self._state_path.read_text())
                except (IOError, TypeError):
                    pass
            self._state = state
            return state

    ## Save methods

    def save(self, state: dict[str, Any] | None = None) -> None:
        with STATE_LOCK:
            if state is not None:
                self._state = state
            if self._state is None:
                return

            tmp = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
            tmp.write_text(json.dumps(self._state, indent=2))
            os.replace(tmp, self._state_path)

    # ----------------------------------------

    ## Get, set, delete, reset methods

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from state.

        Args:
            key: State key to retrieve
            default: Default value if key not found

        Returns:
            Value for key or default
        """
        if self._state is None:
            self.load()
        return (self._state or {}).get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in state and save.

        Args:
            key: State key to set
            value: Value to set
        """
        if self._state is None:
            self.load()
        if self._state is None:
            self._state = {}
        self._state[key] = value
        self.save()

    def delete(self, key: str) -> None:
        """Delete a key from state.

        Args:
            key: State key to delete
        """
        if self._state is None:
            self.load()
        if self._state and key in self._state:
            del self._state[key]
            self.save()

    def reset(self) -> None:
        """Reset state to defaults."""
        self._state = None
        self.initialize()

    # ----------------------------------------

    ## Getters and setters

    def get_current_story(self) -> str:
        """Get the current story.

        Returns:
            The current story
        """
        return self.get("current_story", "")

    def set_current_story(self, story_id: str) -> None:
        """Set the current story.

        Args:
            story_id: The story id
        """
        self.set("current_story", story_id)

    def get_pending_tasks(self, story_id: str) -> list[str]:
        """Get tasks not yet ready, in progress, or completed."""
        tasks = self.get("tasks", {})
        in_progress = set(tasks.get("in_progress", []))
        completed = set(tasks.get("completed", []))
        ready = set(self.get_ready_tasks(story_id))
        exclude = ready | in_progress | completed

        all_tasks = self._config.get_task_list(story_id)
        return [t for t in all_tasks if t not in exclude]

    def get_ready_tasks(self, story_id: str) -> list[str]:
        """Get tasks whose deps are met and aren't already started or done."""
        tasks = self.get("tasks", {})
        in_progress = set(tasks.get("in_progress", []))
        completed = set(tasks.get("completed", []))
        exclude = in_progress | completed

        candidates = self._config.get_tasks_without_deps(story_id)
        tasks_with_deps = self._config.get_tasks_with_deps(story_id)
        for task in tasks_with_deps:
            deps = self._config.get_task_deps(story_id, task)
            if deps and all(dep in completed for dep in deps):
                candidates.append(task)

        return [t for t in candidates if t not in exclude]

    def get_sprint_id(self) -> str:
        """Get the sprint id.

        Returns:
            The sprint id
        """
        return self.get("sprint_id", "")

    def set_sprint_id(self, sprint_id: str) -> None:
        """Set the sprint id.

        Args:
            sprint_id: The sprint id
        """
        self.set("sprint_id", sprint_id)

    # ----------------------------------------
    ## Initializers

    def initialize(self) -> None:
        """Initialize state to defaults."""
        self._state = {
            "sprint_id": "",
            "sprint_completed": False,
            "current_story": "",
            "tasks": {"pending": [], "ready": [], "in_progress": [], "completed": []},
        }
        self.save()

    # ----------------------------------------
    ## Resolvers

    def resolve_tasks(self, story_id: str) -> None:
        """Resolve the tasks.

        Returns:
            The tasks
        """
        tasks = self.get("tasks", {})
        tasks["ready"] = self.get_ready_tasks(story_id)
        tasks["pending"] = self.get_pending_tasks(story_id)
        self.set("tasks", tasks)

    # ----------------------------------------
    ## Status Markers

    def mark_sprint_complete(self) -> bool:
        """Mark the sprint as complete.

        Returns:
            True if the sprint was marked as complete
        """
        self.set("sprint_completed", True)
        return True

    def mark_task(
        self,
        _id: str,
        status: Literal["in_progress", "completed"],
    ) -> tuple[bool, str]:
        """Transition a task to the given status."""
        tasks: dict[str, list[str]] = self.get("tasks", {})
        ready = tasks.get("ready", [])
        in_progress = tasks.get("in_progress", [])
        completed = tasks.get("completed", [])

        if status == "in_progress":
            if _id in completed:
                return False, f"Task '{_id}' is already completed"
            if _id not in ready:
                return False, f"Task '{_id}' is not in ready"
            ready.remove(_id)
            in_progress.append(_id)
            self.set("tasks", tasks)
            return True, f"Task '{_id}' marked as in progress"

        if _id not in in_progress:
            return False, f"Task '{_id}' must be in progress before completing"
        in_progress.remove(_id)
        completed.append(_id)
        self.set("tasks", tasks)
        self.resolve_tasks(self.get_current_story())
        return True, f"Task '{_id}' marked as completed"


if __name__ == "__main__":
    manager = TaskManager()
    print(manager.load())
