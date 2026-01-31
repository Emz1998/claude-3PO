#!/usr/bin/env python3
"""Deliverables configuration and validation for workflow phases."""

import sys
from pathlib import Path
from datetime import datetime
from typing import Any

from typing import Literal
from pydantic import BaseModel, ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.cache import get_session_id

sys.path.insert(0, str(Path(__file__).parent))
from roadmap.project import get_project_milestone_subdir_path  # type: ignore
from roadmap.utils import get_current_milestone_name, get_current  # type: ignore

import yaml


class Deliverable(BaseModel):
    type: Literal["files", "commands", "artifacts"]
    action: Literal["write", "read", "edit", "bash"]
    value: str


class DeliverablesConfig(BaseModel):
    deliverables: dict[str, list[Deliverable]]


CONFIG_PATH = Path(__file__).parent / "config.yaml"

PHASES = ["explore", "plan", "plan-consult", "code", "commit"]
TDD_PHASES = [
    "write-test",
    "review-test",
    "write-code",
    "review-code",
    "refactor",
    "validate",
]
TA_PHASES = [
    "write-code",
    "write-test",
    "review-test",
    "review-code",
    "refactor",
    "validate",
]

DEFAULT_PHASES = ["explore", "plan", "plan-consult", "execute", "commit"]

# Phase -> list of deliverables with type, action, subdir, and prefix
_DELIVERABLES: dict[str, list[dict[str, Any]]] = {
    "explore": [
        {
            "type": "files",
            "action": "write",
            "subdir": "codebase-status",
            "prefix": "codebase-status",
        }
    ],
    "plan": [{"type": "files", "action": "write", "subdir": "plans", "prefix": "plan"}],
    "plan-consult": [
        {
            "type": "files",
            "action": "write",
            "subdir": "consults",
            "prefix": "plan-consultation",
        }
    ],
    "code": [],
    "commit": [
        {"type": "files", "action": "write", "subdir": "reports", "prefix": "commit"}
    ],
    "write-test": [
        {
            "type": "files",
            "action": "write",
            "subdir": "reports",
            "prefix": "test-summary",
        }
    ],
    "review-test": [
        {
            "type": "files",
            "action": "write",
            "subdir": "reports",
            "prefix": "test-quality-report",
        }
    ],
    "write-code": [
        {
            "type": "files",
            "action": "write",
            "subdir": "reports",
            "prefix": "coding-summary",
        }
    ],
    "review-code": [
        {
            "type": "files",
            "action": "write",
            "subdir": "reviews",
            "prefix": "code-review",
        }
    ],
    "refactor": [
        {
            "type": "files",
            "action": "write",
            "subdir": "reports",
            "prefix": "refactoring-summary",
        }
    ],
    "validate": [
        {
            "type": "files",
            "action": "write",
            "subdir": "reports",
            "prefix": "work-completion-report",
        }
    ],
}


def add_deliverable(
    phase: str,
    d_type: str,
    action: Literal["write", "read", "edit", "bash"] = "write",
    **kwargs: Any,
) -> None:
    """Add a deliverable to a phase and optionally write to config."""
    if phase not in _DELIVERABLES:
        _DELIVERABLES[phase] = []
    _DELIVERABLES[phase].append({"type": d_type, "action": action, **kwargs})

    write_to_config()


def resolve(d: dict[str, Any]) -> dict[str, str]:
    """Resolve a deliverable dict to its final form with type, action, and value."""
    d_type = d.get("type", "files")
    action = d.get("action", "write")

    if d_type == "files":
        path = get_project_milestone_subdir_path(d["subdir"])
        value = f"{path}/{d['prefix']}_{get_session_id()}_{datetime.now().strftime('%m%d%Y')}.md"
    elif d_type == "commands":
        value = d.get("command", "")
    elif d_type == "artifacts":
        value = d.get("name", "")
    else:
        value = ""

    return {"type": d_type, "action": action, "value": value}


def get_resolved(phase: str) -> list[dict[str, str]]:
    """Get resolved deliverables as a flat list for a phase."""
    result: list[dict[str, str]] = []
    for d in _DELIVERABLES.get(phase, []):
        resolved = resolve(d)
        if resolved["value"]:
            result.append(resolved)
    return result


def get_all_phases(test_strategy: str = "TDD") -> list[str]:
    """Get all phases in order based on test strategy."""
    list_to_add = DEFAULT_PHASES
    if test_strategy == "TDD":
        list_to_add = TDD_PHASES
    if test_strategy == "TA":
        list_to_add = TA_PHASES
    idx = PHASES.index("code") + 1
    return PHASES[:idx] + list_to_add + PHASES[idx:]


def write_to_config() -> None:
    """Write deliverables to config.yaml as flat list per phase."""
    config: dict[str, Any] = {
        "milestone-id": get_current("milestone"),
        "milestone-name": get_current_milestone_name(),
        "deliverables": {},
    }
    for phase in get_all_phases():
        resolved = get_resolved(phase)
        if resolved:
            config["deliverables"][phase] = resolved
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def load_config(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load and validate config from yaml file. Raises on error."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    if not data:
        raise ValueError("Config file is empty")
    return DeliverablesConfig(**data).model_dump()


def validate_config(data: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    """Validate config data using Pydantic. Returns (is_valid, errors)."""
    if data is None:
        if not CONFIG_PATH.exists():
            return False, ["Config file does not exist"]
        with open(CONFIG_PATH) as f:
            data = yaml.safe_load(f) or {}

    if not data:
        return False, ["Config is empty"]

    try:
        DeliverablesConfig(**data)
        return True, []
    except ValidationError as e:
        return False, [err["msg"] for err in e.errors()]


def check_files_exist(
    config: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """Check if all file deliverables exist. Returns (all_exist, missing_files)."""
    if config is None:
        config = load_config()

    missing: list[str] = []
    for phase_deliverables in config.get("deliverables", {}).values():
        for d in phase_deliverables:
            if d.get("type") == "files" and not Path(d.get("value", "")).exists():
                missing.append(d.get("value", ""))

    return len(missing) == 0, missing
