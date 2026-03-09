from typing import Literal, Union, Any, Generic, TypeVar, Self, cast
from pydantic import BaseModel, model_validator


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
ToolName = Literal["Skill", "Bash", "Write", "Edit", "Read", "EnterPlanMode", "Agent"]


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
    args: str = ""


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


class EnterPlanModeTool(BaseModel):
    pass


class AgentTool(BaseModel):
    description: str
    prompt: str
    subagent_type: str = ""


ToolInputType = Union[SkillTool, BashTool, WriteTool, EditTool, ReadTool, EnterPlanModeTool, AgentTool]

ToolInputMap: dict[str, type[ToolInputType]] = {
    "Skill": SkillTool,
    "Bash": BashTool,
    "Write": WriteTool,
    "Edit": EditTool,
    "Read": ReadTool,
    "EnterPlanMode": EnterPlanModeTool,
    "Agent": AgentTool,
}

T = TypeVar("T", bound=ToolInputType)
U = TypeVar("U", bound=ToolName)


class BaseToolUseInput(HookInput, Generic[T, U]):
    tool_name: U
    tool_input: T
    tool_use_id: str

    @model_validator(mode="before")
    @classmethod
    def set_tool_input(cls, data: Any) -> Any:
        tool_name = data["tool_name"]
        if tool_name:
            data["tool_input"] = ToolInputMap[tool_name](**data["tool_input"])
        return data


class PreToolUseInput(BaseToolUseInput):
    pass


class PostToolUseInput(BaseToolUseInput):
    tool_response: dict[str, Any]


class UserPromptSubmitInput(HookInput):
    prompt: str


class StopInput(HookInput):
    stop_hook_active: bool


if __name__ == "__main__":
    import json
    import sys

    hook_input = json.load(sys.stdin)

    input = PreToolUseInput.model_validate(hook_input)
    print(json.dumps(input.model_dump(), indent=4))
