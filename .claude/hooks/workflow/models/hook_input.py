from typing import Annotated, Literal, Union, Any, Generic, TypeVar, Self
from pydantic import BaseModel, Field, model_validator

import json
import sys


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


PermissionMode = Literal["default", "plan", "acceptEdits", "bypassPermissions"]
ToolName = Literal["Skill", "Bash", "Write", "Edit", "Read"]

T = TypeVar("T", bound=BaseModel, contravariant=True)


class HookInput(BaseModel):
    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: PermissionMode
    hook_event_name: HookEventType

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls.model_validate(data)


class SkillTool(BaseModel):
    skill: str
    args: str


class BashTool(BaseModel):
    command: str
    description: str


class WriteTool(BaseModel):
    file_path: str
    content: str


class EditTool(BaseModel):
    file_path: str
    old_string: str
    new_string: str


class ReadTool(BaseModel):
    file_path: str
    offset: int
    limit: int


ToolInputType = Union[SkillTool, BashTool, WriteTool, EditTool, ReadTool]


class BaseToolUseInput(HookInput, Generic[T]):
    tool_name: ToolName
    tool_input: T
    tool_use_id: str


class PreToolUseInput(BaseToolUseInput, Generic[T]):
    pass


class PostToolUseInput(BaseToolUseInput, Generic[T]):
    tool_response: dict[str, Any]


class UserPromptSubmitInput(HookInput):
    prompt: str


class StopInput(HookInput):
    stop_hook_active: bool
    pass
