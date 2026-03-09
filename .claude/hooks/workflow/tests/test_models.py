"""Tests for Pydantic input/output models."""

import pytest

from workflow.models.hook_input import (
    PreToolUseInput,
    PostToolUseInput,
    UserPromptSubmitInput,
    StopInput,
    SkillTool,
    BashTool,
    WriteTool,
    EditTool,
)
from workflow.models.hook_output import (
    PreToolUseOutput,
    PreToolUseHSO,
    PostToolUseOutput,
    GeneralHSO,
    DecisionControl,
)

from helpers import (
    make_pre_tool_input,
    make_post_tool_input,
    make_user_prompt_input,
    make_stop_input,
)


class TestPreToolUseInput:
    def test_skill_auto_construct(self):
        """PreToolUseInput auto-constructs SkillTool from tool_input dict."""
        data = make_pre_tool_input("Skill", {"skill": "plan", "args": "--verbose"})
        inp = PreToolUseInput.model_validate(data)
        assert isinstance(inp.tool_input, SkillTool)
        assert inp.tool_input.skill == "plan"
        assert inp.tool_input.args == "--verbose"

    def test_bash_auto_construct(self):
        """PreToolUseInput auto-constructs BashTool from tool_input dict."""
        data = make_pre_tool_input("Bash", {"command": "ls", "description": "list"})
        inp = PreToolUseInput.model_validate(data)
        assert isinstance(inp.tool_input, BashTool)
        assert inp.tool_input.command == "ls"

    def test_write_auto_construct(self):
        """PreToolUseInput auto-constructs WriteTool."""
        data = make_pre_tool_input("Write", {"file_path": "/tmp/x.py", "content": "pass"})
        inp = PreToolUseInput.model_validate(data)
        assert isinstance(inp.tool_input, WriteTool)

    def test_edit_auto_construct(self):
        """PreToolUseInput auto-constructs EditTool."""
        data = make_pre_tool_input(
            "Edit",
            {"file_path": "/tmp/x.py", "old_string": "a", "new_string": "b"},
        )
        inp = PreToolUseInput.model_validate(data)
        assert isinstance(inp.tool_input, EditTool)


class TestPostToolUseInput:
    def test_post_tool_use_input(self):
        """PostToolUseInput includes tool_response."""
        data = make_post_tool_input("Bash", {"command": "ls", "description": "list"})
        inp = PostToolUseInput.model_validate(data)
        assert inp.tool_response == {"content": "ok"}
        assert isinstance(inp.tool_input, BashTool)


class TestUserPromptSubmitInput:
    def test_user_prompt_submit(self):
        """UserPromptSubmitInput captures prompt."""
        data = make_user_prompt_input("hello world")
        inp = UserPromptSubmitInput.model_validate(data)
        assert inp.prompt == "hello world"
        assert inp.hook_event_name == "UserPromptSubmit"


class TestStopInput:
    def test_stop_input(self):
        """StopInput captures stop_hook_active."""
        data = make_stop_input(stop_hook_active=True)
        inp = StopInput.model_validate(data)
        assert inp.stop_hook_active is True
        assert inp.hook_event_name == "Stop"


class TestOutputModels:
    def test_pre_tool_use_output(self):
        """PreToolUseOutput with HSO."""
        hso = PreToolUseHSO(permission_decision="deny", permission_decision_reason="blocked")
        output = PreToolUseOutput(hook_specific_output=hso)
        dumped = output.model_dump(by_alias=True)
        assert dumped["hook_specific_output"]["permission_decision"] == "deny"

    def test_post_tool_use_output(self):
        """PostToolUseOutput with decision control."""
        hso = GeneralHSO(hook_event_name="PostToolUse", additional_context="info")
        output = PostToolUseOutput(decision="block", reason="not allowed", hook_specific_output=hso)
        dumped = output.model_dump(by_alias=True)
        assert dumped["decision"] == "block"

    def test_decision_control_defaults(self):
        """DecisionControl defaults to allow."""
        dc = DecisionControl()
        assert dc.decision == "allow"
        assert dc.reason is None
