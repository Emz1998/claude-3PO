#!/usr/bin/env python3
"""Hook event manager for Claude Code hooks."""

from pydantic import BaseModel, model_validator, field_validator
from abc import abstractmethod
import sys
from pathlib import Path
from typing import Any, ClassVar, Literal, LiteralString, get_args, cast, Self
import json

from scripts.claude_hooks.utils.state_store import StateStore  # type: ignore
from scripts.claude_hooks.utils.decision import Output  # type: ignore

HookEventType = Literal[
    "PreToolUse",
    "PostToolUse",
    "Notification",
    "UserPromptSubmit",
    "SessionStart",
    "SessionEnd",
    "Stop",
    "SubagentStop",
]

HOOK_EVENT_TYPES = list(get_args(HookEventType))


class Tool(BaseModel):
    registry: ClassVar[dict[str, type]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls_name = cls.cls_mapper(cls.__name__)
        cls.registry[cls_name] = cls

    @staticmethod
    def cls_mapper(name: str) -> str:
        return name.replace("Tool", "").lower()


class Skill(Tool):
    skill: str | None = None
    args: str | None = None


class Bash(Tool):
    command: str | None = None
    description: str | None = None


class Write(Tool):
    file_path: str | None = None
    content: str | None = None


class Edit(Tool):
    file_path: str | None = None
    old_string: str | None = None
    new_string: str | None = None


class Read(Tool):
    file_path: str | None = None
    offset: int | None = None
    limit: int | None = None


class Hook(BaseModel):
    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: (
        Literal["default", "plan", "acceptEdits", "bypassPermissions"] | None
    ) = None
    hook_event_name: HookEventType

    @model_validator(mode="after")
    def set_hook_event_name(self) -> Self:
        self.hook_event_name = cast(HookEventType, self.__class__.__name__)
        return self

    @staticmethod
    def _read_stdin() -> dict[str, Any]:
        try:
            return json.load(sys.stdin)
        except json.JSONDecodeError:
            return {}

    def set_decision(self, output: Output) -> None:
        print(json.dumps(output.__dict__))
        sys.exit(0)

    def block(self, reason: str) -> None:
        print(reason, file=sys.stderr)
        sys.exit(2)

    def success_response(self, context: str | None = None) -> None:
        if context is None:
            return
        print(context)
        sys.exit(0)

    def run(self) -> None:
        pass


class ToolUse(Hook):

    tool_name: Literal["Skill", "Bash", "Edit", "Read", "Write"]
    tool_input: Skill | Bash | Edit | Read | Write | dict[str, Any]
    tool_use_id: str

    @model_validator(mode="after")
    def set_tool_input(self) -> Self:
        tool_cls = Tool.registry.get(self.tool_name)
        if tool_cls and isinstance(self.tool_input, dict):
            self.tool_input = tool_cls(**self.tool_input)
        elif tool_cls:
            self.tool_input = tool_cls()

        return self


class PreToolUse(ToolUse):
    pass


class PostToolUse(ToolUse):
    tool_response: dict[str, Any]


class Stop(Hook):
    stop_hook_active: bool = False


class UserPromptSubmit(Hook):

    prompt: str


class SessionStart(Hook):
    source: Literal["startup", "resume"]

    @field_validator("permission_mode")
    @classmethod
    def permission_mode_validator(cls, v):
        if v is not None:
            raise ValueError("Permission mode must be None")
        return None

    @model_validator(mode="after")
    def set_permission_mode(self) -> Self:
        delattr(self, "permission_mode")
        return self


if __name__ == "__main__":

    session_start = SessionStart(
        session_id="session_id",
        hook_event_name="SessionStart",
        source="startup",
        transcript_path="transcript_path",
        cwd="cwd",
    )
    print(json.dumps(session_start.model_dump(), indent=4))
