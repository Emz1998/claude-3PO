"""Pure Pydantic models for hook input. No I/O, no sys.exit, no print."""

from pydantic import BaseModel, model_validator
from typing import Any, ClassVar, Literal, Self, cast


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


class Tool(BaseModel):
    registry: ClassVar[dict[str, type]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls_name = cls.__name__.replace("Tool", "").lower()
        cls.registry[cls_name] = cls


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


class HookBase(BaseModel):
    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: (
        Literal["default", "plan", "acceptEdits", "bypassPermissions"] | None
    ) = None
    hook_event_name: HookEventType


class ToolUse(HookBase):
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


class Stop(HookBase):
    stop_hook_active: bool = False


class UserPromptSubmit(HookBase):
    prompt: str
