#!/usr/bin/env python3
"""Validate release-plan.json against schema using Pydantic."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel, Field


class FunctionalRequirement(BaseModel):
    id: str = Field(pattern=r"^FR-\d{3}$")
    description: str


class NonFunctionalRequirement(BaseModel):
    id: str = Field(pattern=r"^NFR-\d{3}$")
    description: str


class Requirements(BaseModel):
    functional: list[FunctionalRequirement]
    non_functional: list[NonFunctionalRequirement]


class SuccessCriteria(BaseModel):
    id: str = Field(pattern=r"^SC-\d{3}$")
    description: str


class AcceptanceCriteria(BaseModel):
    id: str = Field(pattern=r"^AC-\d{3}$")
    description: str


class Task(BaseModel):
    id: str = Field(pattern=r"^T\d{3}$")
    description: str
    dod: str | None = None
    dependencies: list[str]


class UserStory(BaseModel):
    id: str = Field(pattern=r"^US-\d{3}$")
    story: str
    context: str
    acceptance_criteria: list[AcceptanceCriteria]
    tasks: list[Task]


class Feature(BaseModel):
    id: str = Field(pattern=r"^FEAT-\d{3}$")
    title: str
    outcome: str | None = None
    tdd: bool | None = None
    success_criteria: list[SuccessCriteria]
    user_stories: list[UserStory]


class Epic(BaseModel):
    id: str = Field(pattern=r"^EPIC-\d{3}$")
    title: str
    requirements: Requirements
    features: list[Feature]


class Release(BaseModel):
    version: str
    name: str
    target_date: str
    epics: list[Epic]


class ReleasePlan(BaseModel):
    product: str
    vision: str
    releases: list[Release]


def validate_file(file_path: Path, model: type[BaseModel]) -> tuple[bool, str]:
    """Validate a JSON file against a Pydantic model."""
    if not file_path.exists():
        return False, f"File not found: {file_path}"

    try:
        with open(file_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"

    try:
        model.model_validate(data)
        return True, f"{model.__name__} is valid"
    except Exception as e:
        return False, f"Validation error: {e}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate release-plan.json against schema"
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        help="Input release-plan JSON file path",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent

    input_path = project_root / args.input
    is_valid, message = validate_file(input_path, ReleasePlan)
    if is_valid:
        print(f"OK: {message}")
    else:
        print(f"ERROR: {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
