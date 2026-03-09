"""Shared test helpers — factory functions for hook input dicts."""


def make_pre_tool_input(tool_name: str = "Skill", tool_input: dict | None = None, **overrides) -> dict:
    """Build a PreToolUse hook input dict."""
    base = {
        "session_id": "test-session",
        "transcript_path": "/tmp/test.jsonl",
        "cwd": "/tmp",
        "permission_mode": "default",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input or {"skill": "test", "args": ""},
        "tool_use_id": "toolu_test123",
    }
    base.update(overrides)
    return base


def make_post_tool_input(tool_name: str = "Skill", tool_input: dict | None = None, **overrides) -> dict:
    """Build a PostToolUse hook input dict."""
    base = make_pre_tool_input(tool_name, tool_input, **overrides)
    base["hook_event_name"] = "PostToolUse"
    base["tool_response"] = overrides.pop("tool_response", {"content": "ok"})
    return base


def make_user_prompt_input(prompt: str = "hello", **overrides) -> dict:
    """Build a UserPromptSubmit hook input dict."""
    base = {
        "session_id": "test-session",
        "transcript_path": "/tmp/test.jsonl",
        "cwd": "/tmp",
        "permission_mode": "default",
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
    }
    base.update(overrides)
    return base


def make_stop_input(**overrides) -> dict:
    """Build a Stop hook input dict."""
    base = {
        "session_id": "test-session",
        "transcript_path": "/tmp/test.jsonl",
        "cwd": "/tmp",
        "permission_mode": "default",
        "hook_event_name": "Stop",
        "stop_hook_active": True,
    }
    base.update(overrides)
    return base
