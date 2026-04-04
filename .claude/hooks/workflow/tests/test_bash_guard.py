"""Tests for guards/bash_guard.py (new unified version)."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow import recorder
from workflow.guards import bash_guard
from workflow.session_store import SessionStore


def make_state(phase: str, **kwargs) -> dict:
    return {
        "workflow_active": True,
        "workflow_type": "implement",
        "phase": phase,
        "validation_result": kwargs.get("validation_result", None),
        "pr_status": kwargs.get("pr_status", "pending"),
        "ci_status": kwargs.get("ci_status", "pending"),
        "ci_check_executed": kwargs.get("ci_check_executed", False),
        "test_run_executed": kwargs.get("test_run_executed", False),
    }


def write_state(tmp_state_file, state: dict) -> None:
    tmp_state_file.write_text(json.dumps(state))


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
    def test_pr_allowed_when_inactive(self, tmp_state_file):
        tmp_state_file.write_text("")
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(bash_hook("gh pr create --title 'x'"), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# PreToolUse: PR command validation
# ---------------------------------------------------------------------------

class TestPRPreValidation:
    def test_gh_pr_create_allowed_in_pr_create_phase_with_passed_validation(self, tmp_state_file):
        write_state(tmp_state_file, make_state("pr-create", validation_result="Pass"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = bash_guard.validate_pre(bash_hook("gh pr create --title 'x'"), store)
        assert decision == "allow"

    def test_gh_pr_create_blocked_without_validation(self, tmp_state_file):
        write_state(tmp_state_file, make_state("pr-create", validation_result=None))
        store = SessionStore("s", tmp_state_file)
        decision, reason = bash_guard.validate_pre(bash_hook("gh pr create"), store)
        assert decision == "block"
        assert "validation" in reason.lower()

    def test_gh_pr_create_blocked_outside_pr_create_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code", validation_result="Pass"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = bash_guard.validate_pre(bash_hook("gh pr create"), store)
        assert decision == "block"
        assert "pr-create" in reason.lower()

    def test_git_push_blocked_outside_pr_create_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = bash_guard.validate_pre(bash_hook("git push origin main"), store)
        assert decision == "block"

    def test_non_pr_command_always_allowed(self, tmp_state_file):
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
        assert state["test_run_executed"] is True

    def test_non_test_command_not_tracked(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        recorder.record_bash(post_bash_hook("ls -la"), store)
        state = store.load()
        assert state.get("test_run_executed") is False


# ---------------------------------------------------------------------------
# PostToolUse: PR creation tracking
# ---------------------------------------------------------------------------

class TestPRTracking:
    def test_pr_creation_advances_to_ci_check(self, tmp_state_file):
        write_state(tmp_state_file, make_state("pr-create", validation_result="Pass"))
        store = SessionStore("s", tmp_state_file)
        recorder.record_bash(post_bash_hook("gh pr create --title 'x'", output="https://github.com/..."), store)
        state = store.load()
        assert state["phase"] == "ci-check"
        assert state["pr_status"] == "created"

    def test_git_push_advances_to_ci_check(self, tmp_state_file):
        write_state(tmp_state_file, make_state("pr-create", validation_result="Pass"))
        store = SessionStore("s", tmp_state_file)
        recorder.record_bash(post_bash_hook("git push -u origin feature"), store)
        state = store.load()
        assert state["phase"] == "ci-check"


# ---------------------------------------------------------------------------
# PostToolUse: CI check tracking
# ---------------------------------------------------------------------------

class TestCICheckTracking:
    def test_ci_pass_advances_to_report(self, tmp_state_file):
        write_state(tmp_state_file, make_state("ci-check"))
        store = SessionStore("s", tmp_state_file)
        output = "All checks were successful"
        recorder.record_bash(post_bash_hook("gh pr checks 123", output=output), store)
        state = store.load()
        assert state["ci_status"] == "passed"
        assert state["ci_check_executed"] is True
        assert state["phase"] == "report"

    def test_ci_failure_keeps_ci_check_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("ci-check"))
        store = SessionStore("s", tmp_state_file)
        output = "Some checks were not successful"
        recorder.record_bash(post_bash_hook("gh pr checks 123", output=output), store)
        state = store.load()
        assert state["ci_status"] == "failed"
        assert state["phase"] == "ci-check"

    def test_ci_pass_table_format(self, tmp_state_file):
        write_state(tmp_state_file, make_state("ci-check"))
        store = SessionStore("s", tmp_state_file)
        output = "check-1\tpass\t1s\turl\ncheck-2\tpass\t5s\turl"
        recorder.record_bash(post_bash_hook("gh pr checks 1", output=output), store)
        state = store.load()
        assert state["ci_status"] == "passed"
        assert state["phase"] == "report"

    def test_ci_fail_table_format(self, tmp_state_file):
        write_state(tmp_state_file, make_state("ci-check"))
        store = SessionStore("s", tmp_state_file)
        output = "check-1\tpass\t1s\turl\ncheck-2\tfail\t5s\turl"
        recorder.record_bash(post_bash_hook("gh pr checks 1", output=output), store)
        state = store.load()
        assert state["ci_status"] == "failed"
        assert state["phase"] == "ci-check"

    def test_ci_pending_table_format(self, tmp_state_file):
        write_state(tmp_state_file, make_state("ci-check", ci_check_executed=False))
        store = SessionStore("s", tmp_state_file)
        output = "check-1\tpass\t1s\turl\ncheck-2\tpending\t0\turl"
        recorder.record_bash(post_bash_hook("gh pr checks 1", output=output), store)
        state = store.load()
        assert state["ci_check_executed"] is False  # not set until definitive
        assert state["phase"] == "ci-check"

    def test_gh_run_view_with_success_tracked_as_ci(self, tmp_state_file):
        write_state(tmp_state_file, make_state("ci-check"))
        store = SessionStore("s", tmp_state_file)
        recorder.record_bash(post_bash_hook("gh run view 12345", output="check-1\tpass\t1s\turl"), store)
        state = store.load()
        assert state["ci_check_executed"] is True
        assert state["ci_status"] == "passed"
