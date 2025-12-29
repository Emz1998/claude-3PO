#!/usr/bin/env python3
"""Validate roadmap.json against schema using Pydantic."""

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class AcceptanceCriteria(BaseModel):
    id: str = Field(pattern=r"^AC-\d{3}$")
    description: str
    status: Literal["met", "unmet"]


class SuccessCriteria(BaseModel):
    id: str = Field(pattern=r"^SC-\d{3}$")
    description: str
    status: Literal["met", "unmet"]


class Task(BaseModel):
    id: str = Field(pattern=r"^T\d{3}$")
    description: str
    status: Literal["not_started", "in_progress", "completed"]
    parallel: bool
    owner: str
    test_strategy: Literal["TDD", "TA"]
    dependencies: list[str]
    acceptance_criteria: list[AcceptanceCriteria]


class Milestone(BaseModel):
    id: str = Field(pattern=r"^MS-\d{3}$")
    feature: str = Field(pattern=r"^F\d{3}$")
    name: str
    goal: str | None = None
    status: Literal["not_started", "in_progress", "completed"]
    dependencies: list[str]
    mcp_servers: list[str]
    success_criteria: list[SuccessCriteria]
    tasks: list[Task]


class Phase(BaseModel):
    id: str = Field(pattern=r"^PH-\d{3}$")
    name: str
    status: Literal["not_started", "in_progress", "completed"]
    checkpoint: bool | None = None
    milestones: list[Milestone]


class Current(BaseModel):
    phase: str = Field(pattern=r"^PH-\d{3}$")
    milestone: str = Field(pattern=r"^MS-\d{3}$")
    task: str = Field(pattern=r"^T\d{3}$")


class SummaryCount(BaseModel):
    total: int = Field(ge=0)
    pending: int = Field(ge=0)
    completed: int = Field(ge=0)


class Summary(BaseModel):
    phases: SummaryCount
    milestones: SummaryCount
    tasks: SummaryCount


class Metadata(BaseModel):
    last_updated: str
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")


class Roadmap(BaseModel):
    name: str
    version: str
    target_release: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: Literal["not_started", "in_progress", "completed"]
    phases: list[Phase]
    current: Current
    summary: Summary
    metadata: Metadata


def validate_roadmap(file_path: Path) -> tuple[bool, str]:
    """Validate roadmap JSON file against schema."""
    if not file_path.exists():
        return False, f"File not found: {file_path}"

    try:
        with open(file_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"

    try:
        Roadmap.model_validate(data)
        return True, "Roadmap is valid"
    except Exception as e:
        return False, f"Validation error: {e}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate roadmap.json against schema")
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="project/roadmap.json",
        help="Input JSON file path (default: project/roadmap.json)",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent
    input_path = project_root / args.input

    is_valid, message = validate_roadmap(input_path)

    if is_valid:
        print(f"OK: {message}")
        sys.exit(0)
    else:
        print(f"ERROR: {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
