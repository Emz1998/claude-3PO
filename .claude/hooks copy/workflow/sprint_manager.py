#!/usr/bin/env python3
"""Unified state manager for workflow orchestration.

Provides a clean API for workflow state operations, wrapping state.json.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Literal

from scripts.claude_hooks.sprint import SprintConfig, StoryManager, TaskManager, StateStore  # type: ignore

PROJECT_ROOT = Path.cwd()
STATE_PATH = PROJECT_ROOT / "project/sprints/SPRINT-001/status.json"


class Sprint:
    """Sprint manager for workflow orchestration."""

    def __init__(self, state: StateStore, config: SprintConfig):
        """Initialize the sprint manager.

        Args:
            sprint_id: The sprint id
        """
        self._state = state
        self._config = config
        self._story = StoryManager(self._state, self._config)
        self._task = TaskManager(self._state, self._config)

    @property
    def story(self) -> StoryManager:
        """Get the story manager."""
        return self._story

    @story.setter
    def story(self, story: StoryManager) -> None:
        """Set the story manager."""
        self._story = story

    @property
    def task(self) -> TaskManager:
        """Get the task manager."""
        return self._task

    @task.setter
    def task(self, task: TaskManager) -> None:
        """Set the task manager."""
        self._task = task

    def mark_sprint_complete(self) -> bool:
        """Mark the sprint as complete.

        Returns:
            True if the sprint was marked as complete
        """
        self._state.set("sprint_completed", True)
        return True

    def get_sprint_id(self) -> str:
        """Get the sprint id.

        Returns:
            The sprint id
        """
        return self._state.get("sprint_id", "")


if __name__ == "__main__":

    sprint = Sprint(StateStore(STATE_PATH), SprintConfig())
    print(sprint.story.current)
