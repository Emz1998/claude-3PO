from dataclasses import dataclass, field
from typing import Any, Literal, TypeVar, Generic
from datetime import datetime


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
class SprintMetadata:
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SprintMetadata":
        return cls(
            created_at=raw.get("created_at", ""),
            updated_at=raw.get("updated_at", ""),
        )


@dataclass
class SprintState:
    metadata: SprintMetadata = field(default_factory=SprintMetadata)
    sprint_id: str = "SPRINT-001"
    status: Literal["not_started", "in_progress", "completed"] = "not_started"
    current_story: str = ""
    stories: Bucket = field(default_factory=Bucket)
    tasks: TaskBucket[Bucket] = field(default_factory=TaskBucket[Bucket])

    @staticmethod
    def next_sprint_id(sprint_id: str) -> str:
        """SPRINT-001 -> SPRINT-002."""
        prefix, num = sprint_id.rsplit("-", 1)
        return f"{prefix}-{int(num) + 1:03d}"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SprintState":
        stories = raw.get("stories", {})
        metadata = SprintMetadata.from_dict(raw.get("metadata", {}))
        tasks = TaskBucket[Bucket]()
        for sid, b in raw.get("tasks", {}).items():
            tasks[sid] = Bucket(**b) if isinstance(b, dict) else Bucket()
        return cls(
            metadata=metadata,
            sprint_id=raw.get("sprint_id", "SPRINT-001"),
            status=raw.get("status", "not_started"),
            current_story=raw.get("current_story", ""),
            stories=Bucket(**stories) if isinstance(stories, dict) else Bucket(),
            tasks=tasks,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "sprint_id": self.sprint_id,
            "status": self.status,
            "current_story": self.current_story,
            "stories": vars(self.stories),
            "tasks": {sid: vars(b) for sid, b in self.tasks.items.items()},
        }
