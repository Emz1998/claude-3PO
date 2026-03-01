"""Tests for workflow gate — handlers skip unless workflow is activated.

The workflow_active flag is set by build_entry and implement_trigger handlers.
All other handlers must check this flag and return early if not active.
"""

import json
import os
import subprocess
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FLAG_FILE = PROJECT_ROOT / "project/tmp/tmp_state.json"


# --- State flag tests ---


class TestWorkflowState:
    """The workflow_active flag in session state controls handler execution."""

    def test_workflow_active_defaults_to_false(self):
        from scripts.claude_hooks.handlers.workflow_gate import is_workflow_active

        # With no state file / empty state, should return False
        mock_state = {}
        assert is_workflow_active(mock_state) is False

    def test_workflow_active_true_when_set(self):
        from scripts.claude_hooks.handlers.workflow_gate import is_workflow_active

        mock_state = {"workflow_active": True}
        assert is_workflow_active(mock_state) is True

    def test_workflow_active_false_when_explicitly_false(self):
        from scripts.claude_hooks.handlers.workflow_gate import is_workflow_active

        mock_state = {"workflow_active": False}
        assert is_workflow_active(mock_state) is False


class TestActivationHandlers:
    """build_entry and implement_trigger must set workflow_active=True."""

    def test_activate_workflow_sets_flag(self):
        from scripts.claude_hooks.handlers.workflow_gate import activate_workflow, WORKFLOW_FLAG

        with patch.object(WORKFLOW_FLAG, "read", return_value={}), \
             patch.object(WORKFLOW_FLAG, "write") as mock_write:
            activate_workflow()
            mock_write.assert_called_once_with({"workflow_active": True})


class TestGatedHandlers:
    """All workflow handlers (except build_entry/implement_trigger) must check the gate."""

    GATED_HANDLERS = [
        "phase_guard",
        "log_guard",
        "commit_guard",
        "session_recorder",
        "logging_reminder",
        "parallel_tasks",
        "stop_guard",
    ]

    @pytest.mark.parametrize("handler_name", GATED_HANDLERS)
    def test_handler_skips_when_gate_inactive(self, handler_name):
        """Each gated handler returns without side effects when workflow is inactive."""
        import importlib

        mod = importlib.import_module(f"scripts.claude_hooks.handlers.{handler_name}")
        with patch(
            f"scripts.claude_hooks.handlers.{handler_name}.check_workflow_gate",
            return_value=False,
        ):
            # Provide minimal valid hook input
            hook_input = {
                "session_id": "test",
                "transcript_path": "/tmp/test.json",
                "cwd": str(PROJECT_ROOT),
                "hook_event_name": "PreToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "explore"},
                "tool_use_id": "tu-test",
                "tool_response": {"status": "ok"},
                "prompt": "hello",
            }
            # Should return without raising or blocking
            result = mod.handle(hook_input)
            assert result is None


class TestGateBypass:
    """Handlers that activate the workflow are NOT gated."""

    def test_build_entry_returns_on_non_matching_prompt(self):
        """build_entry returns cleanly when prompt doesn't start with /build."""
        from scripts.claude_hooks.handlers import build_entry

        hook_input = {
            "session_id": "test",
            "transcript_path": "/tmp/test.json",
            "cwd": str(PROJECT_ROOT),
            "hook_event_name": "UserPromptSubmit",
            "prompt": "some random prompt",
        }
        result = build_entry.handle(hook_input)
        assert result is None

    def test_implement_trigger_returns_on_non_matching_prompt(self):
        """implement_trigger returns cleanly when prompt doesn't start with /implement."""
        from scripts.claude_hooks.handlers import implement_trigger

        hook_input = {
            "session_id": "test",
            "transcript_path": "/tmp/test.json",
            "cwd": str(PROJECT_ROOT),
            "hook_event_name": "UserPromptSubmit",
            "prompt": "some random prompt",
        }
        result = implement_trigger.handle(hook_input)
        assert result is None


class TestDispatcherGateIntegration:
    """Dispatchers should pass through when workflow is inactive (handlers skip)."""

    @pytest.fixture(autouse=True)
    def _deactivate_workflow(self):
        """Ensure workflow is inactive for dispatcher subprocess tests."""
        backup = None
        if FLAG_FILE.exists():
            backup = FLAG_FILE.read_text()
        FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
        FLAG_FILE.write_text(json.dumps({"workflow_active": False}))
        yield
        if backup is not None:
            FLAG_FILE.write_text(backup)
        else:
            FLAG_FILE.unlink(missing_ok=True)

    def _run_dispatcher(
        self, event: str, stdin_data: str
    ) -> subprocess.CompletedProcess:
        script = PROJECT_ROOT / f".claude/hooks/dispatchers/{self._script_name(event)}"
        return subprocess.run(
            [sys.executable, str(script)],
            input=stdin_data,
            text=True,
            capture_output=True,
            env={**__import__("os").environ, "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT)},
        )

    @staticmethod
    def _script_name(event: str) -> str:
        return {
            "PreToolUse": "pre_tool.py",
            "PostToolUse": "post_tool.py",
            "Stop": "stop.py",
            "UserPromptSubmit": "user_prompt.py",
        }[event]

    def test_pre_tool_exits_0_when_workflow_inactive(self):
        """With no workflow_active flag, PreToolUse handlers should not block."""
        data = json.dumps(
            {
                "session_id": "gate-test",
                "transcript_path": "/tmp/test.json",
                "cwd": str(PROJECT_ROOT),
                "hook_event_name": "PreToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "explore"},
                "tool_use_id": "tu-gate",
            }
        )
        result = self._run_dispatcher("PreToolUse", data)
        # Should exit 0 (all handlers skip because workflow not active)
        assert result.returncode == 0

    def test_post_tool_exits_0_when_workflow_inactive(self):
        data = json.dumps(
            {
                "session_id": "gate-test",
                "transcript_path": "/tmp/test.json",
                "cwd": str(PROJECT_ROOT),
                "hook_event_name": "PostToolUse",
                "tool_name": "Skill",
                "tool_input": {"skill": "explore"},
                "tool_use_id": "tu-gate",
                "tool_response": {"status": "ok"},
            }
        )
        result = self._run_dispatcher("PostToolUse", data)
        assert result.returncode == 0

    def test_stop_exits_0_when_workflow_inactive(self):
        data = json.dumps(
            {
                "session_id": "gate-test",
                "transcript_path": "/tmp/test.json",
                "cwd": str(PROJECT_ROOT),
                "hook_event_name": "Stop",
            }
        )
        result = self._run_dispatcher("Stop", data)
        assert result.returncode == 0
