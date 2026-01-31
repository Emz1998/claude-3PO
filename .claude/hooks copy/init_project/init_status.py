#!/usr/bin/env python3
"""Initialize project status based on status-json-template.md schema."""

import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import write_file  # type: ignore

STATUS_FILE_PATH = Path("project/status.json")


class SpecStatus(BaseModel):
    status: str = "not_started"
    path: str


class Specs(BaseModel):
    prd: SpecStatus = Field(default_factory=lambda: SpecStatus(path="specs/prd.md"))
    tech: SpecStatus = Field(default_factory=lambda: SpecStatus(path="specs/tech.md"))
    ux: SpecStatus = Field(default_factory=lambda: SpecStatus(path="specs/ux.md"))


class CountSummary(BaseModel):
    total: int = 0
    completed: int = 0


class Summary(BaseModel):
    phases: CountSummary = Field(default_factory=CountSummary)
    milestones: CountSummary = Field(default_factory=CountSummary)
    tasks: CountSummary = Field(default_factory=CountSummary)


class Current(BaseModel):
    phase: str | None = None
    milestone: str | None = None
    task: str | None = None


class Project(BaseModel):
    name: str = "Project Name"
    version: str = "0.1.0"
    target_release: str = "2026-01-01"
    status: str = "not_started"


class Metadata(BaseModel):
    last_updated: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    schema_version: str = "1.0.0"


class Status(BaseModel):
    project: Project = Field(default_factory=Project)
    specs: Specs = Field(default_factory=Specs)
    summary: Summary = Field(default_factory=Summary)
    current: Current = Field(default_factory=Current)
    phases: dict = Field(default_factory=dict)
    metadata: Metadata = Field(default_factory=Metadata)


def init_status(
    project_name: str = "Project Name",
    version: str = "0.1.0",
    target_release: str = "2026-01-01",
) -> Status:
    """Initialize a new project status with default values."""
    status = Status(
        project=Project(
            name=project_name,
            version=version,
            target_release=target_release,
            status="not_started",
        ),
        specs=Specs(),
        summary=Summary(),
        current=Current(),
        phases={},
        metadata=Metadata(),
    )
    return status


def save_status(status: Status, path: Path = STATUS_FILE_PATH) -> bool:
    """Save status to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_file(str(path), status.model_dump_json(indent=2))
    return True


def init_and_save_status(
    project_name: str = "Project Name",
    version: str = "0.1.0",
    target_release: str = "2026-01-01",
    path: Path = STATUS_FILE_PATH,
) -> bool:
    """Initialize and save project status to file."""
    status = init_status(project_name, version, target_release)
    return save_status(status, path)


if __name__ == "__main__":
    # Default initialization when run directly
    init_and_save_status()
    print(f"Status initialized at {STATUS_FILE_PATH}")
