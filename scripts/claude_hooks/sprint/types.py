from dataclasses import dataclass, field
from typing import Any, Literal, TypeVar, Generic


T = TypeVar("T")

Status = Literal["pending", "ready", "in_progress", "completed"]


@dataclass
class Bucket:
    pending: list[str] = field(default_factory=list)
    ready: list[str] = field(default_factory=list)
    in_progress: list[str] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)


@dataclass
class TaskBucket(Generic[T]):
    items: dict[str, T] = field(default_factory=dict)

    def add(self, ticket_id: str, value: T) -> None:
        self.items[ticket_id] = value

    def get(self, ticket_id: str) -> T | None:
        return self.items.get(ticket_id)

    def __contains__(self, ticket_id: str) -> bool:
        return ticket_id in self.items

    def __getitem__(self, ticket_id: str) -> T:
        return self.items[ticket_id]

    def __setitem__(self, ticket_id: str, value: T) -> None:
        self.items[ticket_id] = value


@dataclass
class SprintState:
    sprint_id: str = ""
    sprint_completed: bool = False
    current_story: str = ""
    stories: Bucket = field(default_factory=Bucket)
    tasks: TaskBucket[Bucket] = field(default_factory=TaskBucket[Bucket])

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SprintState":
        stories = raw.get("stories", {})
        tasks = TaskBucket[Bucket]()
        for sid, b in raw.get("tasks", {}).items():
            tasks[sid] = Bucket(**b) if isinstance(b, dict) else Bucket()
        return cls(
            sprint_id=raw.get("sprint_id", ""),
            sprint_completed=raw.get("sprint_completed", False),
            current_story=raw.get("current_story", ""),
            stories=Bucket(**stories) if isinstance(stories, dict) else Bucket(),
            tasks=tasks,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sprint_id": self.sprint_id,
            "sprint_completed": self.sprint_completed,
            "current_story": self.current_story,
            "stories": vars(self.stories),
            "tasks": {sid: vars(b) for sid, b in self.tasks.items.items()},
        }
