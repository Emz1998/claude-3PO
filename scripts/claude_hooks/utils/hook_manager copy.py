#!/usr/bin/env python3
"""Hook event manager for Claude Code hooks."""

from dataclasses import dataclass
from abc import abstractmethod
import sys
from pathlib import Path
from typing import Any
import json

from scripts.claude_hooks.utils.state_store import StateStore  # type: ignore
from scripts.claude_hooks.utils.decision import Output  # type: ignore


class ToolInput(dict):
    """Dict with attribute access for tool inputs."""

    def __getattr__(self, key: str) -> Any:
        return self.get(key)


@dataclass
class HookInput:
    """Unified input for all 15 hook event types."""

    # Common fields (all events)
    session_id: str | None = None
    transcript_path: str | None = None
    cwd: str | None = None
    permission_mode: str | None = None
    hook_event_name: str | None = None
    # Tool events (PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest)
    tool_name: str | None = None
    tool_input: ToolInput | None = None
    tool_response: dict[str, Any] | None = None
    tool_use_id: str | None = None
    # PostToolUseFailure
    error: str | None = None
    is_interrupt: bool | None = None
    # PermissionRequest
    permission_suggestions: list[dict[str, Any]] | None = None
    # SessionStart
    source: str | None = None
    model: str | None = None
    agent_type: str | None = None
    # Stop, SubagentStop
    stop_hook_active: bool | None = None
    last_assistant_message: str | None = None
    # SubagentStart, SubagentStop
    agent_id: str | None = None
    agent_transcript_path: str | None = None
    # SessionEnd
    reason: str | None = None
    # UserPromptSubmit
    prompt: str | None = None
    # Notification
    message: str | None = None
    title: str | None = None
    notification_type: str | None = None
    # PreCompact
    trigger: str | None = None
    custom_instructions: str | None = None
    # TeammateIdle, TaskCompleted
    teammate_name: str | None = None
    team_name: str | None = None
    # TaskCompleted
    task_id: str | None = None
    task_subject: str | None = None
    task_description: str | None = None
    # ConfigChange
    file_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


class Hook:

    # def __init__(self, test: bool = True):

    #     if test is False:
    #         self._raw = self._read_stdin()
    #         self._input: HookInput = self._resolve(self._raw)
    #     self._input = HookInput()

    def init(self):
        self._raw = self._read_stdin()
        self._input = self._resolve(self._raw)

    def load_test_data(
        self, hook_event_name: str, tool_name: str | None = None
    ) -> None:
        tool_events = {
            "PreToolUse",
            "PostToolUse",
            "PostToolUseFailure",
            "PermissionRequest",
        }
        if hook_event_name in tool_events and tool_name is None:
            raise ValueError("tool_name is required for tool events")

        base = Path.cwd() / "input-schemas"
        if hook_event_name in tool_events:
            tool_name = tool_name.strip().lower() if tool_name else ""
            subdir = "pre_tool" if hook_event_name == "PreToolUse" else "post_tool"
            path = base / subdir / f"{tool_name}.json"
        else:
            path = base / f"{hook_event_name.lower()}.json"

        self._raw = StateStore(path).load()
        self._input = self._resolve(self._raw)

    @property
    def input(self) -> HookInput:
        return self._input

    @input.setter
    def input(self, value: HookInput) -> None:
        self._input = value

    def set_decision(self, output: Output) -> None:
        print(json.dumps(output.__dict__))
        sys.exit(0)

    def block(self, reason: str) -> None:
        print(reason, file=sys.stderr)
        sys.exit(2)

    @staticmethod
    def _read_stdin() -> dict[str, Any]:
        try:
            return json.load(sys.stdin)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _resolve(data: dict[str, Any]) -> HookInput:
        data = {**data}
        # Wrap raw tool_input dict for attribute access
        tool_input = data.get("tool_input")
        if isinstance(tool_input, dict):
            data["tool_input"] = ToolInput(tool_input)
        return HookInput(**data)

    def run(self) -> None:
        pass


if __name__ == "__main__":

    hook = Hook()
