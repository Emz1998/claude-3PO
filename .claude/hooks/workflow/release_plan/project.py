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

from workflow.release_plan.state import get_current_epic_id, get_current_feature_id, load_project_state  # type: ignore

FeatureSubdir = Literal[
    "codebase-status",
    "reports",
    "decisions",
    "plans",
    "research",
    "reviews",
    "misc",
    "todos",
    "consults",
    "revisions",
]
VALID_FEATURE_SUBDIRS = get_args(FeatureSubdir)

STATE = load_project_state()


def get_project_dir(query: Literal["rel", "abs"] = "rel") -> Path:
    project_dir = Path("project")
    return project_dir.absolute() if query == "abs" else project_dir


def get_project_version_path(query: Literal["rel", "abs"] = "rel") -> Path:
    return get_project_dir(query) / STATE.get("current_version", "")


def get_project_epic_path(query: Literal["rel", "abs"] = "rel") -> Path:
    return get_project_version_path(query) / get_current_epic_id(STATE)


def get_feature_path(query: Literal["rel", "abs"] = "rel") -> Path:
    return get_project_epic_path(query) / get_current_feature_id(STATE)


def get_feature_subdir_path(
    subdir: FeatureSubdir, query: Literal["rel", "abs"] = "rel"
) -> Path | list[str]:
    return get_feature_path(query) / subdir


def get_all_feature_subdir_paths(
    query: Literal["rel", "abs"] = "rel",
) -> list[str]:
    return [
        str(get_feature_subdir_path(subdir, query)) for subdir in VALID_FEATURE_SUBDIRS
    ]


if __name__ == "__main__":
    print(get_project_dir())
    print(get_project_version_path())
    print(get_feature_subdir_path("codebase-status"))
    pprint(get_all_feature_subdir_paths())
