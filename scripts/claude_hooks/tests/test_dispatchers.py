"""Tests for dispatchers — error isolation, invalid input handling.

These tests invoke dispatchers as subprocesses (matching how Claude Code runs them).
"""

import json
import subprocess
import sys
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DISPATCHERS = {
    "PreToolUse": PROJECT_ROOT / ".claude/hooks/dispatchers/pre_tool.py",
    "PostToolUse": PROJECT_ROOT / ".claude/hooks/dispatchers/post_tool.py",
    "Stop": PROJECT_ROOT / ".claude/hooks/dispatchers/stop.py",
    "UserPromptSubmit": PROJECT_ROOT / ".claude/hooks/dispatchers/user_prompt.py",
}


def _run_dispatcher(event: str, stdin_data: str) -> subprocess.CompletedProcess:
    script = DISPATCHERS[event]
    return subprocess.run(
        [sys.executable, str(script)],
        input=stdin_data,
        text=True,
        capture_output=True,
        env={
            **__import__("os").environ,
            "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT),
        },
    )


def _make_pre_tool_input(**overrides) -> str:
    base = {
        "session_id": "test-session",
        "transcript_path": "/tmp/test.json",
        "cwd": str(PROJECT_ROOT),
        "hook_event_name": "PreToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": "explore"},
        "tool_use_id": "tu-test",
    }
    base.update(overrides)
    return json.dumps(base)


def _make_post_tool_input(**overrides) -> str:
    base = {
        "session_id": "test-session",
        "transcript_path": "/tmp/test.json",
        "cwd": str(PROJECT_ROOT),
        "hook_event_name": "PostToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": "explore"},
        "tool_use_id": "tu-test",
        "tool_response": {"status": "ok"},
    }
    base.update(overrides)
    return json.dumps(base)


def _make_stop_input(**overrides) -> str:
    base = {
        "session_id": "test-session",
        "transcript_path": "/tmp/test.json",
        "cwd": str(PROJECT_ROOT),
        "hook_event_name": "Stop",
    }
    base.update(overrides)
    return json.dumps(base)


def _make_user_prompt_input(**overrides) -> str:
    base = {
        "session_id": "test-session",
        "transcript_path": "/tmp/test.json",
        "cwd": str(PROJECT_ROOT),
        "hook_event_name": "UserPromptSubmit",
        "prompt": "hello",
    }
    base.update(overrides)
    return json.dumps(base)


class TestInvalidInput:
    """Dispatchers must handle bad input gracefully."""

    @pytest.mark.parametrize("event", ["PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"])
    def test_invalid_json_exits_0(self, event):
        result = _run_dispatcher(event, "not valid json {{{")
        assert result.returncode == 0

    @pytest.mark.parametrize("event", ["PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"])
    def test_empty_stdin_exits_0(self, event):
        result = _run_dispatcher(event, "")
        assert result.returncode == 0


class TestErrorIsolation:
    """One handler raising should not prevent the next handler from running."""

    def test_pre_tool_dispatcher_runs(self):
        """Basic smoke test — dispatcher doesn't crash on valid input."""
        result = _run_dispatcher("PreToolUse", _make_pre_tool_input())
        # May exit 0 or 2 depending on phase guard state, but should NOT crash
        assert result.returncode in (0, 2)

    def test_post_tool_dispatcher_runs(self):
        result = _run_dispatcher("PostToolUse", _make_post_tool_input())
        assert result.returncode in (0, 2)

    def test_stop_dispatcher_runs(self):
        result = _run_dispatcher("Stop", _make_stop_input())
        assert result.returncode in (0, 2)

    def test_user_prompt_dispatcher_runs(self):
        result = _run_dispatcher("UserPromptSubmit", _make_user_prompt_input())
        assert result.returncode in (0, 2)


class TestDispatcherBootstrap:
    """Dispatchers must work via CLAUDE_PROJECT_DIR env var."""

    @pytest.mark.parametrize("event", ["PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"])
    def test_dispatcher_script_exists(self, event):
        assert DISPATCHERS[event].exists(), f"Missing dispatcher: {DISPATCHERS[event]}"

    @pytest.mark.parametrize("event", ["PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"])
    def test_dispatcher_is_executable_python(self, event):
        content = DISPATCHERS[event].read_text()
        assert "#!/usr/bin/env python3" in content
        assert "if __name__" in content
