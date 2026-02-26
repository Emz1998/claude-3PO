#!/usr/bin/env python3
"""Unified state manager for workflow orchestration.

Provides a clean API for workflow state operations, wrapping state.json.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Literal

STATE_PATH = Path("project/sprints/SPRINT-001") / "status.json"


class SprintManager:
    """Sprint manager for workflow orchestration."""

    def __init__(self, state_path: Path = STATE_PATH):
        """Initialize the state manager.

        Args:
            state_path: Path to the state.json file
        """
        self._state_path = state_path
        self._state: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        """Load state from file.

        Returns:
            State dictionary
        """
        if self._state_path.exists():
            try:
                self._state = json.loads(self._state_path.read_text())
            except (json.JSONDecodeError, IOError, TypeError):
                self._state = {}
        else:
            self._state = {}

        return self._state or {}

    def save(self, state: dict[str, Any] | None = None) -> None:
        """Save state to file.

        Args:
            state: State dictionary to save (uses internal state if None)
        """
        if state is not None:
            self._state = state
        if self._state is not None:
            self._state_path.write_text(json.dumps(self._state, indent=2))

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

    def initialize(self) -> None:
        """Initialize state to defaults."""
        self._state = {
            "sprint_id": "",
            "sprint_complete": False,
            "current_story": "",
            "tasks": {},
            "deliverables": {},
            "history": {
                "stories": [],
                "tasks": [],
                "deliverables": [],
            },
        }
        self.save()

    def reset(self) -> None:
        """Reset state to defaults."""
        self._state = None
        self.initialize()

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

    def mark_sprint_complete(self) -> bool:
        """Mark the sprint as complete.

        Returns:
            True if the sprint was marked as complete
        """
        self.set("sprint_complete", True)
        return True

    def get_current_story(self) -> str:
        """Get the current story.

        Returns:
            The current story
        """
        return self.get("current_story", "")

    def set_current_story(self, story: str) -> None:
        """Set the current story.

        Args:
            story: The current story
        """
        self.set("current_story", story)

    def mark_story_complete(self, story_id: str) -> bool:
        """Mark a story as complete.

        Args:
            story_id: The id of the story to mark as complete
        """
        history = self.get("history", {})
        history["stories"].append(story_id)
        self.set("history", history)
        return True

    def get_deliverables(self) -> list[dict[str, Any]]:
        """Get the deliverables.

        Returns:
            The deliverables
        """
        return self.get("deliverables", [])

    def set_deliverables(self, deliverables: list[dict[str, Any]]) -> None:
        """Set deliverables for current phase.

        Args:
            deliverables: List of deliverable dictionaries
        """
        self.set("deliverables", deliverables)

    def mark_deliverable_complete(
        self,
        deliverable_id: str,
    ) -> bool:
        """Mark a deliverable as completed.

        Args:
            deliverable_id: The id of the deliverable to mark
            status: The status to mark the deliverable as
        """

        history = self.get("history", {})
        history["deliverables"].append(deliverable_id)
        self.set("history", history)
        return True

    def get_tasks(self) -> dict[str, Any]:
        """Get the tasks.

        Returns:
            The tasks
        """
        return self.get("tasks", {})

    def set_tasks(self, tasks: dict[str, Any]) -> None:
        """Set the tasks.

        Args:
            tasks: The tasks
        """
        self.set("tasks", tasks)

    def mark_task_complete(self, task_id: str) -> bool:
        """Mark a task as complete.

        Args:
            task_id: The id of the task to mark as complete
        """
        history = self.get("history", {})
        history["tasks"].append(task_id)
        self.set("history", history)
        return True

    def get_history(self) -> dict[str, Any]:
        """Get the history.

        Returns:
            The history
        """
        return self.get("history", {})

    def set_history(self, history: dict[str, Any]) -> None:
        """Set the history.

        Args:
            history: The history
        """
        self.set("history", history)

    def get_stories_history(self) -> list[str]:
        """Get the stories history.

        Returns:
            The stories history
        """
        return self.get("history", {}).get("stories", [])

    def set_stories_history(self, stories: list[str]) -> None:
        """Set the stories history.

        Args:
            stories: The stories history
        """
        self.set("history", {"stories": stories})

    def get_tasks_history(self) -> list[str]:
        """Get the tasks history.

        Returns:
            The tasks history
        """
        return self.get("history", {}).get("tasks", [])

    def get_current_task(self) -> str:
        """Get the current task.

        Returns:
            The current task
        """
        return self.get("current_task", "")

    def set_current_task(self, task: str) -> None:
        """Set the current task.

        Args:
            task: The current task
        """
        self.set("current_task", task)

    def 

    # def activate_troubleshoot(self) -> None:
    #     """Activate troubleshoot mode and store current phase."""
    #     current = self.get_current_phase()
    #     self.set("pre_troubleshoot_phase", current)
    #     self.set("troubleshoot", True)
    #     self.set_current_phase("troubleshoot")

    # def deactivate_troubleshoot(self) -> None:
    #     """Deactivate troubleshoot and return to previous phase."""
    #     previous = self.get("pre_troubleshoot_phase")
    #     self.set("troubleshoot", False)
    #     if previous:
    #         self.set_current_phase(previous)
    #     self.delete("pre_troubleshoot_phase")

    # def reset_deliverables_status(self) -> None:
    #     """Reset all deliverables to incomplete."""
    #     deliverables = self.get_deliverables()
    #     for d in deliverables:
    #         d["completed"] = False
    #     self.set_deliverables(deliverables)


if __name__ == "__main__":
    sprint_manager = SprintManager()

    sprint_manager.resolve_story(
        {
            "stories": [
                {
                    "id": "US-001",
                    "dependsOn": [],
                    "tasks": [
                        {
                            "id": "T-001",
                            "dependsOn": [],
                        },
                        {
                            "id": "T-002",
                            "dependsOn": ["T-001"],
                        },
                    ],
                },
                {
                    "id": "US-002",
                    "dependsOn": [],
                    "tasks": [
                        {
                            "id": "T-003",
                            "dependsOn": ["T-001"],
                        },
                        {
                            "id": "T-004",
                            "dependsOn": ["T-002"],
                        },
                    ],
                },
                {
                    "id": "US-003",
                    "dependsOn": ["US-001"],
                    "tasks": [
                        {
                            "id": "T-005",
                            "dependsOn": ["T-003"],
                        },
                    ],
                },
            ]
        }
    )

    sprint_manager.resolve_task(
        {
            "tasks": [
                {
                    "id": "T-001",
                    "dependsOn": [],
                },
            ],
        },
    )

    # print(sprint_manager.get_current_story())
    print(sprint_manager.get_current_task())
