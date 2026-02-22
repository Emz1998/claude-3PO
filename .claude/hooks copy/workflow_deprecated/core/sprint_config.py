#!/usr/bin/env python3
"""Unified state manager for workflow orchestration.

Provides a clean API for workflow state operations, wrapping state.json.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Type, TypeVar, Optional
from dataclasses import dataclass

STATE_PATH = Path("project/sprints/SPRINT-001") / "sprint.json"


class SprintConfig:
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

    def get_project_name(self) -> str:
        """Get the project name.

        Returns:
            The project name
        """
        return self.get("project", "")

    def set_project_name(self, project_name: str) -> None:
        """Set the project name.

        Args:
            project_name: The project name
        """
        self.set("project", project_name)

    def get_sprint_number(self) -> str:
        """Get the sprint number.

        Returns:
            The sprint number
        """
        return self.get("sprint", "")

    def set_sprint_number(self, sprint_number: str) -> None:
        """Set the sprint number.

        Args:
            sprint_number: The sprint number
        """
        self.set("sprint", sprint_number)

    def get_goal(self) -> str:
        """Get the goal.

        Returns:
            The goal
        """
        return self.get("goal", "")

    def set_goal(self, goal: str) -> None:
        """Set the goal.

        Args:
            goal: The goal
        """
        self.set("goal", goal)

    def get_dates(self) -> dict[str, Any]:
        """Get the dates.

        Returns:
            The dates
        """
        return self.get("dates", {})

    def set_dates(self, dates: dict[str, Any]) -> None:
        """Set the dates.

        Args:
            dates: The dates
        """
        self.set("dates", dates)

    def get_capacity(self) -> dict[str, Any]:
        """Get the capacity.

        Returns:
            The capacity
        """
        return self.get("capacity", {})

    def set_capacity(self, capacity: dict[str, Any]) -> None:
        """Set the capacity.

        Args:
            capacity: The capacity
        """
        self.set("capacity", capacity)

    def get_total_points(self) -> int:
        """Get the total points.

        Returns:
            The total points
        """
        return self.get("total_points", 0)

    def set_total_points(self, total_points: int) -> None:
        """Set the total points.

        Args:
            total_points: The total points
        """
        self.set("total_points", total_points)

    def get_tasks_history(self) -> list[str]:
        """Get the tasks history.

        Returns:
            The tasks history
        """
        return self.get("history", {}).get("tasks", [])

    def get_stories(self) -> list[dict[str, Any]]:
        """Get the stories.

        Returns:
            The stories
        """
        return self.get("stories", [])

    def set_stories(self, stories: list[dict[str, Any]]) -> None:
        """Set the stories.

        Args:
            stories: The stories
        """
        self.set("stories", stories)

    def find_story(self, story_id: str) -> dict[str, Any] | None:
        """Get the story by id.

        Args:
            story: The story
        """
        stories = self.get("stories", [])

        for story in stories:
            if story.get("id") != story_id:
                continue
            return story
        print(f"Story {story_id} not found")
        return None

    def create_us_context(self, story_id: str) -> str:
        """Create a context for a story.

        Args:
            story_id: The story id
        """
        story = self.find_story(story_id)
        if story is None:
            return f"Story {story_id} not found"
        return f"Story {story_id} found"
