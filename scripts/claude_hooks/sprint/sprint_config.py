#!/usr/bin/env python3
"""Unified state manager for workflow orchestration.

Provides a clean API for workflow state operations, wrapping sprint.json.
"""

from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

from scripts.claude_hooks.utils.file_manager import FileManager

PROJECT_ROOT = Path.cwd()
STATE_PATH = PROJECT_ROOT / "project/sprints/SPRINT-001/overview/sprint.json"


@dataclass
class Task:
    id: str = ""
    title: str = ""
    status: str = "Todo"
    complexity: str = "S"
    depends_on: list[str] = field(default_factory=list)
    qa_loops: list[int] = field(default_factory=lambda: [0, 3])
    code_review_loops: list[int] = field(default_factory=lambda: [0, 2])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            status=data.get("status", "Todo"),
            complexity=data.get("complexity", "S"),
            depends_on=data.get("dependsOn", []),
            qa_loops=data.get("qaLoops", [0, 3]),
            code_review_loops=data.get("codeReviewLoops", [0, 2]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "complexity": self.complexity,
            "dependsOn": self.depends_on,
            "qaLoops": self.qa_loops,
            "codeReviewLoops": self.code_review_loops,
        }


@dataclass
class Story:
    id: str = ""
    type: str = ""
    epic: Optional[str] = None
    title: str = ""
    points: int = 0
    status: str = "Todo"
    depends_on: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    priority: str = ""
    timebox: str = ""
    deliverables: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Story":
        return cls(
            id=data.get("id", ""),
            type=data.get("type", ""),
            epic=data.get("epic"),
            title=data.get("title", ""),
            points=data.get("points", 0),
            status=data.get("status", "Todo"),
            depends_on=data.get("dependsOn", []),
            blocked_by=data.get("blockedBy", []),
            priority=data.get("priority", ""),
            timebox=data.get("timebox", ""),
            deliverables=data.get("deliverables", []),
            tasks=[Task.from_dict(t) for t in data.get("tasks", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "epic": self.epic,
            "title": self.title,
            "points": self.points,
            "status": self.status,
            "dependsOn": self.depends_on,
            "blockedBy": self.blocked_by,
        }
        if self.priority:
            result["priority"] = self.priority
        if self.timebox:
            result["timebox"] = self.timebox
        if self.deliverables:
            result["deliverables"] = self.deliverables
        if self.tasks:
            result["tasks"] = [t.to_dict() for t in self.tasks]
        return result

    def find_task(self, task_id: str) -> Optional[Task]:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_task_ids(self) -> list[str]:
        return [t.id for t in self.tasks]

    def get_tasks_with_deps(self) -> list[str]:
        return [t.id for t in self.tasks if t.depends_on]

    def get_tasks_without_deps(self) -> list[str]:
        return [t.id for t in self.tasks if not t.depends_on]


@dataclass
class Dates:
    start: str = ""
    end: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Dates":
        return cls(start=data.get("start", ""), end=data.get("end", ""))

    def to_dict(self) -> dict[str, str]:
        return {"start": self.start, "end": self.end}


@dataclass
class Capacity:
    hours: int = 0
    weeks: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Capacity":
        return cls(hours=data.get("hours", 0), weeks=data.get("weeks", 0))

    def to_dict(self) -> dict[str, int]:
        return {"hours": self.hours, "weeks": self.weeks}


@dataclass
class Sprint:
    project: str = ""
    sprint: int = 0
    goal: str = ""
    dates: Dates = field(default_factory=Dates)
    capacity: Capacity = field(default_factory=Capacity)
    total_points: int = 0
    stories: list[Story] = field(default_factory=list)
    completed_points: int = 0
    progress: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Sprint":
        return cls(
            project=data.get("project", ""),
            sprint=data.get("sprint", 0),
            goal=data.get("goal", ""),
            dates=Dates.from_dict(data.get("dates", {})),
            capacity=Capacity.from_dict(data.get("capacity", {})),
            total_points=data.get("totalPoints", 0),
            stories=[Story.from_dict(s) for s in data.get("stories", [])],
            completed_points=data.get("completedPoints", 0),
            progress=data.get("progress", 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "sprint": self.sprint,
            "goal": self.goal,
            "dates": self.dates.to_dict(),
            "capacity": self.capacity.to_dict(),
            "totalPoints": self.total_points,
            "stories": [s.to_dict() for s in self.stories],
            "completedPoints": self.completed_points,
            "progress": self.progress,
        }

    def find_story(self, story_id: str) -> Optional[Story]:
        for story in self.stories:
            if story.id == story_id:
                return story
        return None

    def get_story_ids(self) -> list[str]:
        return [s.id for s in self.stories]

    def get_stories_with_deps(self) -> list[str]:
        return [s.id for s in self.stories if s.depends_on]

    def get_stories_without_deps(self) -> list[str]:
        return [s.id for s in self.stories if not s.depends_on]


class SprintConfig:
    """Sprint config loader. Delegates queries to Sprint/Story dataclasses."""

    def __init__(self, state_path: Path = STATE_PATH):
        self._fm = FileManager(state_path)
        self._sprint: Optional[Sprint] = None

    def load(self) -> Sprint:
        data = self._fm.load() or {}
        self._sprint = Sprint.from_dict(data)
        return self._sprint

    def save(self) -> None:
        if self._sprint is not None:
            self._fm.save(self._sprint.to_dict())

    @property
    def sprint(self) -> Sprint:
        if self._sprint is None:
            self.load()
        assert self._sprint is not None
        return self._sprint
