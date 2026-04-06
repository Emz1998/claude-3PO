"""Tests for guards/bash_guard.py — build version (no PR/CI gating)."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from build import recorder
from build.guards import bash_guard
from build.session_store import SessionStore


def make_state(phase: str, **kwargs) -> dict:
    return {
        "workflow_active": True,
        "workflow_type": "build",
        "phase": phase,
        "validation_result": kwargs.get("validation_result", None),
        "tests": {
            "file_paths": [],
            "review_result": None,
            "executed": kwargs.get("test_executed", False),
        },
    }


def write_state(tmp_state_file, state: dict) -> None:
    SessionStore("s", tmp_state_file).save(state)


def bash_hook(command: str, output: str = "") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"output": output},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def post_bash_hook(command: str, output: str = "") -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"output": output},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


# ---------------------------------------------------------------------------
# Inactive workflow — all allowed
# ---------------------------------------------------------------------------

class TestWorkflowInactive:
    def test_bash_allowed_when_inactive(self, tmp_state_file):
        tmp_state_file.write_text("")
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(bash_hook("gh pr create --title 'x'"), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# Commit format validation
# ---------------------------------------------------------------------------

class TestCommitFormat:
    def test_valid_conventional_commit(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(bash_hook("git commit -m 'feat: add login'"), store)
        assert decision == "allow"

    def test_invalid_commit_blocked(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = bash_guard.validate_pre(bash_hook("git commit -m 'bad message'"), store)
        assert decision == "block"
        assert "conventional commit" in reason.lower()

    def test_non_commit_always_allowed(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(bash_hook("pytest tests/"), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# PostToolUse: test-run tracking
# ---------------------------------------------------------------------------

class TestTestRunTracking:
    @pytest.mark.parametrize("command", [
        "pytest tests/",
        "npm test",
        "yarn test",
        "go test ./...",
        "jest --coverage",
        "vitest run",
    ])
    def test_test_run_commands_tracked(self, command, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = SessionStore("s", tmp_state_file)
        recorder.record_bash(post_bash_hook(command), store)
        state = store.load()
        assert state["tests"]["executed"] is True

    def test_non_test_command_not_tracked(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        recorder.record_bash(post_bash_hook("ls -la"), store)
        state = store.load()
        assert state.get("tests", {}).get("executed") is False
