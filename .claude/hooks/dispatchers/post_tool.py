#!/usr/bin/env python3
"""Recorder for hook events."""

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Any, Type
import json
import re
from dataclasses import fields, dataclass

from scripts.claude_hooks.utils.state_store import StateStore  # type: ignore
from scripts.claude_hooks.utils.decision import Output  # type: ignore


@dataclass
class ToolInput:
    def from_dict(self, data: dict[str, Any]) -> "ToolInput":
        data = data or {}
        allowed = {f.name for f in fields(self)}
        filtered = {k: v for k, v in data.items() if k in allowed}
        return self.__class__(**filtered)  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass
class ReadToolInput(ToolInput):
    file_path: str | None = None
    offset: int | None = None
    limit: int | None = None


@dataclass
class WriteToolInput(ToolInput):
    file_path: str | None = None
    content: str | None = None


@dataclass
class TaskToolInput(ToolInput):
    description: str | None = None
    prompt: str | None = None
    subagent_type: str | None = None


@dataclass
class SkillToolInput(ToolInput):
    skill: str | None = None
    args: str | None = None


@dataclass
class BashToolInput(ToolInput):
    command: str | None = None
    description: str | None = None


@dataclass
class EditToolInput(ToolInput):
    file_path: str | None = None
    old_string: str | None = None
    new_string: str | None = None
