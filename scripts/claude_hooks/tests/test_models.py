"""Tests for models.py — pure Pydantic models, no I/O."""

import pytest
from typing import Any


def test_tool_classes_has_all_tool_types():
    from scripts.claude_hooks.models import TOOL_CLASSES

    expected = {"Skill", "Bash", "Write", "Edit", "Read"}
    assert expected == set(TOOL_CLASSES.keys())


def test_skill_model_parses():
    from scripts.claude_hooks.models import Skill

    s = Skill(skill="explore", args="--verbose")
    assert s.skill == "explore"
    assert s.args == "--verbose"


def test_skill_model_optional_fields():
    from scripts.claude_hooks.models import Skill

    s = Skill()
    assert s.skill is None
    assert s.args is None


def test_pre_tool_use_parses_minimal():
    from scripts.claude_hooks.models import PreToolUse

    data = {
        "session_id": "abc",
        "transcript_path": "/tmp/t.json",
        "cwd": "/home",
        "hook_event_name": "PreToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": "explore"},
        "tool_use_id": "tu-1",
    }
    hook = PreToolUse(**data)
    assert hook.session_id == "abc"
    assert hook.hook_event_name == "PreToolUse"


def test_pre_tool_use_auto_parses_tool_input():
    from scripts.claude_hooks.models import PreToolUse, Skill

    data = {
        "session_id": "abc",
        "transcript_path": "/tmp/t.json",
        "cwd": "/home",
        "hook_event_name": "PreToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": "plan", "args": "task T-001 in_progress"},
        "tool_use_id": "tu-1",
    }
    hook = PreToolUse(**data)
    assert isinstance(hook.tool_input, Skill)
    assert hook.tool_input.skill == "plan"
    assert hook.tool_input.args == "task T-001 in_progress"


def test_post_tool_use_has_tool_response():
    from scripts.claude_hooks.models import PostToolUse

    data = {
        "session_id": "abc",
        "transcript_path": "/tmp/t.json",
        "cwd": "/home",
        "hook_event_name": "PostToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": "explore"},
        "tool_use_id": "tu-1",
        "tool_response": {"status": "ok"},
    }
    hook = PostToolUse(**data)
    assert hook.tool_response == {"status": "ok"}


def test_stop_model():
    from scripts.claude_hooks.models import Stop

    data = {
        "session_id": "abc",
        "transcript_path": "/tmp/t.json",
        "cwd": "/home",
        "hook_event_name": "Stop",
    }
    hook = Stop(**data)
    assert hook.stop_hook_active is False


def test_user_prompt_submit_model():
    from scripts.claude_hooks.models import UserPromptSubmit

    data = {
        "session_id": "abc",
        "transcript_path": "/tmp/t.json",
        "cwd": "/home",
        "hook_event_name": "UserPromptSubmit",
        "prompt": "/implement US-001",
    }
    hook = UserPromptSubmit(**data)
    assert hook.prompt == "/implement US-001"


def test_models_have_no_io_methods():
    """Models must not have block(), success_response(), _read_stdin()."""
    from scripts.claude_hooks import models

    for cls_name in ["PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"]:
        cls = getattr(models, cls_name)
        assert not hasattr(cls, "block"), f"{cls_name} should not have block()"
        assert not hasattr(cls, "success_response"), f"{cls_name} should not have success_response()"
        assert not hasattr(cls, "_read_stdin"), f"{cls_name} should not have _read_stdin()"
