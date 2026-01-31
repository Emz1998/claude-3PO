#!/usr/bin/env python3
# Project utilities for status loggers

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, get_args
from pprint import pprint

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.json import load_json, save_json  # type: ignore
from roadmap.utils import get_current_version, get_current_phase_name, get_current_milestone_name  # type: ignore

MilestoneSubdir = Literal[
    "codebase-status",
    "reports",
    "decisions",
    "plans",
    "research",
    "reviews",
    "misc",
    "todos",
    "consults",
]
VALID_MILESTONE_SUBDIRS = get_args(MilestoneSubdir)


def get_project_dir(query: Literal["rel", "abs"] = "rel") -> Path:
    project_dir = Path("project")
    return project_dir.absolute() if query == "abs" else project_dir


def get_project_version_path(query: Literal["rel", "abs"] = "rel") -> Path:
    return get_project_dir(query) / get_current_version()


def get_project_phase_dir_path(query: Literal["rel", "abs"] = "rel") -> Path:
    return get_project_version_path(query) / f"{get_current_phase_name()}"


def get_project_milestone_dir_path(query: Literal["rel", "abs"] = "rel") -> Path:
    return get_project_phase_dir_path(query) / f"{get_current_milestone_name()}"


def get_project_milestone_subdir_path(
    subdir: MilestoneSubdir, query: Literal["rel", "abs"] = "rel"
) -> Path | list[str]:
    return get_project_milestone_dir_path(query) / subdir


def get_all_project_milestone_subdir_paths(
    query: Literal["rel", "abs"] = "rel",
) -> list[str]:
    return [
        str(get_project_milestone_dir_path(query) / subdir)
        for subdir in VALID_MILESTONE_SUBDIRS
    ]


if __name__ == "__main__":
    print(get_project_dir())
    print(get_project_version_path())
    print(get_project_phase_dir_path())
    print(get_project_milestone_dir_path())
    print(get_project_milestone_subdir_path("codebase-status"))
    pprint(get_all_project_milestone_subdir_paths())
