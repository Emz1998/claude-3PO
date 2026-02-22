#!/usr/bin/env python3
"""Recorder for hook events."""

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Any, Union, TypedDict
import json
import re


try:
    from .state import StateManager
    from .decision import Output
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.state import StateManager  # type: ignore
    from utils.decision import Output  # type: ignore


def block(reason: str) -> None:
    """Block the hook."""
    print(reason, file=sys.stderr)
    sys.exit(2)


class ToolInput:
    def get(self, key: str) -> Any:
        return self.__dict__.get(key)

    def set(self, key: str, value: Any) -> None:
        self.__dict__[key] = value


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


@dataclass
class Input:
    session_id: str | None = None
    transcript_path: str | None = None
    cwd: str | None = None
    permission_mode: str | None = None
    hook_event_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the hook input to a dictionary."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class PreToolUse(Input):

    tool_name: str | None = None
    tool_input: (
        ReadToolInput
        | WriteToolInput
        | TaskToolInput
        | SkillToolInput
        | BashToolInput
        | EditToolInput
        | None
    ) = None
    tool_use_id: str | None = None


@dataclass
class PostToolUse(Input):
    tool_name: str | None = None
    tool_input: (
        ReadToolInput
        | WriteToolInput
        | TaskToolInput
        | SkillToolInput
        | BashToolInput
        | EditToolInput
        | None
    ) = None
    tool_response: dict[str, Any] | None = None
    tool_use_id: str | None = None


InputTypes = Union[PreToolUse, PostToolUse]

TOOL_INPUT_MAP: dict[str, type] = {
    "Read": ReadToolInput,
    "Write": WriteToolInput,
    "Task": TaskToolInput,
    "Skill": SkillToolInput,
    "Bash": BashToolInput,
    "Edit": EditToolInput,
}


class Hook:

    def __init__(self, test: bool = False):
        if test:
            self._stdin: dict[str, Any] = {}
        else:
            self._stdin = self.read_stdin_json()
            self._input = self.resolve_input()

    def test(self, hook_event_name: str, tool_name: str | None = None) -> None:
        """Test the hook."""

        if hook_event_name in ["PreToolUse", "PostToolUse"] and tool_name is None:
            raise ValueError("Tool name is required for PreToolUse and PostToolUse")

        tool_name = tool_name.strip().lower() if tool_name else None

        if hook_event_name == "PreToolUse":
            path = Path.cwd() / "input-schemas" / "pre_tool" / f"{tool_name}.json"
        elif hook_event_name == "PostToolUse":
            path = Path.cwd() / "input-schemas" / "post_tool" / f"{tool_name}.json"
        else:
            raise ValueError(f"Invalid hook event name: {hook_event_name}")
        state_manager = StateManager(path)

        self._stdin = state_manager.load()
        self._input = self.resolve_input()

    def read_stdin_json(self) -> dict[str, Any]:
        """Parse JSON from stdin. Returns empty dict on error."""
        try:
            return json.load(sys.stdin)
        except json.JSONDecodeError:
            return {}

    @property
    def input(self) -> InputTypes:
        """Get the hook input."""
        return self._input

    @input.setter
    def input(self, value: InputTypes) -> None:
        """Set the hook input."""
        self._input = value

    def resolve_input(self) -> InputTypes:
        hook_event_name = self._stdin.get("hook_event_name")
        data = {**self._stdin}

        # Convert tool_input dict to the appropriate dataclass
        tool_input = data.get("tool_input")
        tool_name = data.get("tool_name", "")
        if isinstance(tool_input, dict) and tool_name in TOOL_INPUT_MAP:
            data["tool_input"] = TOOL_INPUT_MAP[tool_name](**tool_input)

        if hook_event_name == "PreToolUse":
            return PreToolUse(**data)
        elif hook_event_name == "PostToolUse":
            return PostToolUse(**data)
        else:
            raise ValueError(f"Invalid hook event name: {hook_event_name}")

    def set_decision(self, output: Output) -> None:
        """Output the hook response."""
        print(json.dumps(output.__dict__))
        sys.exit(0)

    def block(self, reason: str) -> None:
        """Block the hook."""
        print(reason, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    hook = Hook()
    hook.test("PreToolUse", "Write")
