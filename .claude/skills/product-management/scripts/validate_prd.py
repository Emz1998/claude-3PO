#!/usr/bin/env python3
"""Validate PRD.json against schema using Pydantic."""

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AcceptanceCriteria(BaseModel):
    id: str = Field(pattern=r"^AC-\d{3}$")
    criteria: str


class UserStory(BaseModel):
    id: str = Field(pattern=r"^US-\d{3}$")
    title: str
    story: str
    acceptance_criteria: list[AcceptanceCriteria]

    @field_validator("story")
    @classmethod
    def validate_story_format(cls, v: str) -> str:
        if not v.startswith("As a"):
            raise ValueError("Story must follow format: 'As a [role], I want...'")
        return v


class Requirement(BaseModel):
    id: str
    description: str


class FunctionalRequirement(Requirement):
    id: str = Field(pattern=r"^FR-\d{3}$")


class NonFunctionalRequirement(Requirement):
    id: str = Field(pattern=r"^NFR-\d{3}$")


class Requirements(BaseModel):
    functional: list[FunctionalRequirement]
    non_functional: list[NonFunctionalRequirement]


class Dependency(BaseModel):
    id: str = Field(pattern=r"^D\d{3}$")
    dependency: str
    assumption: str


class Risk(BaseModel):
    id: str = Field(pattern=r"^R\d{3}$")
    title: str
    overview: str
    impact: str
    probability: Literal["Low", "Medium", "High"]
    mitigation: str


class SuccessCriteria(BaseModel):
    id: str = Field(pattern=r"^SC-\d{3}$")
    title: str
    description: str


class Feature(BaseModel):
    id: str = Field(pattern=r"^F\d{3}$")
    name: str
    description: str
    user_stories: list[UserStory]
    requirements: Requirements
    dependencies: list[Dependency]
    risks: list[Risk]
    success_criteria: list[SuccessCriteria]


class Version(BaseModel):
    version: str = Field(pattern=r"^v\d+\.\d+\.\d+$")
    release_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: Literal["not_started", "in_progress", "completed", "released"]
    features: list[Feature]


class Overview(BaseModel):
    name: str
    type: str
    elevator_pitch: str
    industry_problem: str
    solutions: list[str]
    goals: list[str]


class Metadata(BaseModel):
    last_updated: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    updated_by: str


class PRD(BaseModel):
    current_version: str = Field(pattern=r"^v\d+\.\d+\.\d+$")
    stable_version: str = Field(pattern=r"^v\d+\.\d+\.\d+$")
    overview: Overview
    versions: list[Version]
    tech_stack: list[str]
    metadata: Metadata


def validate_prd(file_path: Path) -> tuple[bool, str]:
    """Validate PRD JSON file against schema."""
    if not file_path.exists():
        return False, f"File not found: {file_path}"

    try:
        with open(file_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"

    try:
        PRD.model_validate(data)
        return True, "PRD is valid"
    except Exception as e:
        return False, f"Validation error: {e}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate PRD.json against schema")
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="project/product/PRD.json",
        help="Input JSON file path (default: project/product/PRD.json)",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent
    input_path = project_root / args.input

    is_valid, message = validate_prd(input_path)

    if is_valid:
        print(f"OK: {message}")
        sys.exit(0)
    else:
        print(f"ERROR: {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
