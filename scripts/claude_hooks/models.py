"""Pure Pydantic models for hook input. No I/O, no sys.exit, no print."""

from pydantic import BaseModel, model_validator, field_validator, ValidationInfo
from typing import Any, Literal, Self
import sys
import json


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
    def __getattr__(self, name: str) -> Any:
        return None


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


TOOL_CLASSES: dict[str, type[Tool]] = {
    "Skill": Skill,
    "Bash": Bash,
    "Write": Write,
    "Edit": Edit,
    "Read": Read,
}

# Python field name -> JSON key mapping


class HookBase(BaseModel):
    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: (
        Literal["default", "plan", "acceptEdits", "bypassPermissions"] | None
    ) = None
    hook_event_name: HookEventType

    def block(self, reason: str) -> None:
        """Block the hook (exit 2 + stderr message)."""
        print(reason, file=sys.stderr)
        sys.exit(2)

    def debug(self, message: str | None = None) -> None:
        """Print a debug message (exit 0 if message given)."""
        if message is None:
            return
        print(message)
        sys.exit(1)

    def succeed(self, context: str | None = None) -> None:
        """Allow the hook, optionally printing context (exit 0 if context given)."""
        if context is None:
            return
        print(context)
        sys.exit(0)

    def field_map(self) -> dict[str, str]:
        return {
            "continue_": "continue",
            "stop_reason": "stopReason",
            "suppress_output": "suppressOutput",
            "system_message": "systemMessage",
            "decision": "decision",
            "reason": "reason",
            "hook_specific_output": "hookSpecificOutput",
        }

    def build_output(self, **kwargs: Any) -> str:
        """Build a JSON string with camelCase keys, omitting None values."""
        result = {}
        for py_key, value in kwargs.items():
            if value is None:
                continue
            json_key = self.field_map().get(py_key, py_key)
            result[json_key] = value
        return json.dumps(result)

    def set_decision(self, **kwargs: Any) -> None:
        """Print JSON output and exit 0."""
        print(self.build_output(**kwargs))
        sys.exit(0)


class ToolUse(HookBase):
    tool_name: Literal["Skill", "Bash", "Edit", "Read", "Write"]
    tool_input: Tool
    tool_use_id: str

    @field_validator("tool_input", mode="before")
    @classmethod
    def normalize_tool_input(cls, v: Any, info: ValidationInfo) -> Tool:
        tool_name = info.data.get("tool_name")
        if tool_name is None:
            # tool_name not available yet (ordering / missing input)
            raise ValueError(
                "tool_name is required before tool_input can be normalized"
            )

        tool_cls = TOOL_CLASSES.get(tool_name)
        if tool_cls is None:
            raise ValueError(f"Invalid tool name: {tool_name}")

        if isinstance(v, Tool):
            return v

        if isinstance(v, dict):
            return tool_cls(**v)

        raise TypeError(
            f"tool_input must be a dict or Tool instance, got {type(v).__name__}"
        )


class PreToolUse(ToolUse):
    pass


class PostToolUse(ToolUse):
    tool_response: dict[str, Any]


class Stop(HookBase):
    stop_hook_active: bool = False


class UserPromptSubmit(HookBase):
    prompt: str
