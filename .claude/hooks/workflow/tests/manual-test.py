#!/usr/bin/env python3
"""Dry run test for Claude Code hook dispatchers.

Simulates a realistic hook workflow by piping JSON input to dispatchers
via subprocess, matching how Claude Code invokes hooks at runtime.
"""

import sys
import time
from dataclasses import dataclass
from pathlib import Path
import subprocess
import json
import re
from typing import Any

import shutil

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from workflow.lib.file_manager import FileManager


# Hook events that require tool_name
TOOL_EVENTS = {"PreToolUse", "PostToolUse", "EnterPlanMode"}

ALL_EVENTS = {
    *TOOL_EVENTS,
    "PostToolUseFailure",
    "PermissionRequest",
    "UserPromptSubmit",
    "Notification",
    "SubagentStart",
    "SubagentStop",
    "PreCompact",
    "SessionEnd",
    "SessionStart",
    "Stop",
}


def camel_to_underscore(name: str) -> str:
    parts = re.findall(r"[A-Z][a-z]*", name)
    return "_".join(parts).lower()  # type: ignore


def resolve_schema_path(hook_event: str, tool_name: str | None = None) -> Path:
    """Resolve the input schema JSON path for a hook event."""
    if hook_event not in ALL_EVENTS:
        raise ValueError(f"Invalid hook event: {hook_event}")
    if hook_event in TOOL_EVENTS and tool_name is None:
        raise ValueError(f"tool_name required for {hook_event}")

    base = Path.cwd() / "input-schemas"
    if hook_event in TOOL_EVENTS:
        subdir = camel_to_underscore(hook_event)
        tool_name = camel_to_underscore(tool_name) if tool_name else None
        return base / subdir / f"{tool_name}.json".lower()

    return base / f"{camel_to_underscore(hook_event)}.json"


class SchemaLoader:
    """Loads and patches hook input JSON from schema files."""

    def __init__(self, hook_event: str, tool_name: str | None = None):
        path = resolve_schema_path(hook_event, tool_name)
        self._file = FileManager(path, lock=False)
        self._data: dict[str, Any] = dict(self._file.load() or {})

    def patch(self, overrides: dict[str, Any]) -> None:
        self._data.update(overrides)
        self._file.save(self._data)

    def to_json(self) -> str:
        return json.dumps(self._data)

    @property
    def data(self) -> dict[str, Any]:
        return self._data


def run_test(script: Path, input_json: str) -> None:
    """Run a dispatcher script with JSON piped to stdin."""

    subprocess.run([sys.executable, str(script)], input=input_json, text=True)


if __name__ == "__main__":
    script = Path(".claude/hooks/workflow/handlers/review_trigger.py")
    schema = SchemaLoader("UserPromptSubmit")
    schema.patch({"prompt": "/review 287"})

    print(json.dumps(schema.data, indent=4))
    run_test(script, json.dumps(schema.data, indent=4))
