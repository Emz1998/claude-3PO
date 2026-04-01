"""Tests for guards/write_guard.py (new unified version)."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow.guards import write_guard
from workflow.state_store import StateStore


def make_state(phase: str, **kwargs) -> dict:
    return {
        "workflow_active": True,
        "workflow_type": kwargs.get("workflow_type", "implement"),
        "phase": phase,
        "tdd": kwargs.get("tdd", True),
        "plan_file": kwargs.get("plan_file", None),
        "plan_written": kwargs.get("plan_written", False),
        "test_files_created": kwargs.get("test_files_created", []),
        "report_written": kwargs.get("report_written", False),
        "agents": [],
    }


def write_state(tmp_state_file, state: dict) -> None:
    tmp_state_file.write_text(json.dumps(state))


def write_hook(file_path: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "x"},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def edit_hook(file_path: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path, "old_string": "a", "new_string": "b"},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def post_write_hook(file_path: str) -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "# Plan"},
        "tool_response": {"type": "update", "filePath": file_path},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


# ---------------------------------------------------------------------------
# Inactive workflow — all writes allowed
# ---------------------------------------------------------------------------

class TestInactiveWorkflow:
    def test_write_allowed_when_workflow_inactive(self, tmp_state_file):
        tmp_state_file.write_text("{}")
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# Write-plan / review phases
# ---------------------------------------------------------------------------

class TestWritePlanPhase:
    def test_plan_write_allowed_to_plans_dir(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook(".claude/plans/my-plan.md"), store)
        assert decision == "allow"

    def test_code_write_blocked_in_write_plan(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = StateStore(tmp_state_file)
        decision, reason = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "block"
        assert "plan" in reason.lower()

    def test_claude_config_write_always_allowed(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook(".claude/settings.json"), store)
        assert decision == "allow"

    def test_non_code_file_always_allowed(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("README.md"), store)
        assert decision == "allow"


class TestReviewPhase:
    def test_plan_write_allowed_in_review(self, tmp_state_file):
        write_state(tmp_state_file, make_state("review", plan_written=True))
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook(".claude/plans/my-plan.md"), store)
        assert decision == "allow"

    def test_code_write_blocked_in_review(self, tmp_state_file):
        write_state(tmp_state_file, make_state("review"))
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "block"


# ---------------------------------------------------------------------------
# Write-tests phase
# ---------------------------------------------------------------------------

class TestWriteTestsPhase:
    def test_test_file_allowed_in_write_tests(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("tests/test_foo.py"), store)
        assert decision == "allow"

    def test_code_file_blocked_in_write_tests(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = StateStore(tmp_state_file)
        decision, reason = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "block"
        assert "test" in reason.lower()

    def test_test_file_tracked_in_post(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = StateStore(tmp_state_file)
        write_guard.handle_post(post_write_hook("tests/test_foo.py"), store)
        state = store.load()
        assert "tests/test_foo.py" in state["test_files_created"]

    def test_non_code_file_allowed_in_write_tests(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("package.json"), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# Write-code phase
# ---------------------------------------------------------------------------

class TestWriteCodePhase:
    def test_code_write_allowed_in_write_code(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "allow"

    def test_edit_allowed_in_write_code(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(edit_hook("src/app.py"), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# Validate / pr-create phases
# ---------------------------------------------------------------------------

class TestValidatePhase:
    def test_code_write_blocked_in_validate(self, tmp_state_file):
        write_state(tmp_state_file, make_state("validate"))
        store = StateStore(tmp_state_file)
        decision, reason = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "block"
        assert "validate" in reason.lower()

    def test_code_write_blocked_in_pr_create(self, tmp_state_file):
        write_state(tmp_state_file, make_state("pr-create"))
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "block"


# ---------------------------------------------------------------------------
# CI-check phase — code write triggers regression
# ---------------------------------------------------------------------------

class TestCICheckPhase:
    def test_code_write_allowed_in_ci_check(self, tmp_state_file):
        write_state(tmp_state_file, make_state("ci-check"))
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "allow"

    def test_code_write_in_ci_check_triggers_regression(self, tmp_state_file):
        write_state(tmp_state_file, make_state("ci-check"))
        store = StateStore(tmp_state_file)
        write_guard.handle_post(post_write_hook("src/app.py"), store)
        state = store.load()
        assert state["phase"] == "write-code"
        assert state["ci_status"] == "pending"
        assert state["validation_result"] is None
        assert state["pr_status"] == "pending"


# ---------------------------------------------------------------------------
# Report phase
# ---------------------------------------------------------------------------

class TestReportPhase:
    def test_report_write_allowed_to_reports_dir(self, tmp_state_file):
        write_state(tmp_state_file, make_state("report"))
        store = StateStore(tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook(".claude/reports/latest-report.md"), store)
        assert decision == "allow"

    def test_code_write_blocked_in_report(self, tmp_state_file):
        write_state(tmp_state_file, make_state("report"))
        store = StateStore(tmp_state_file)
        decision, reason = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "block"


# ---------------------------------------------------------------------------
# PostToolUse: plan file tracking
# ---------------------------------------------------------------------------

class TestPlanWritePost:
    def test_plan_write_to_plans_dir_sets_plan_written(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = StateStore(tmp_state_file)
        write_guard.handle_post(post_write_hook(".claude/plans/my-plan.md"), store)
        state = store.load()
        assert state["plan_written"] is True
        assert state["plan_file"] == ".claude/plans/my-plan.md"
        assert state["phase"] == "review"

    def test_non_plan_write_does_not_set_plan_written(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = StateStore(tmp_state_file)
        write_guard.handle_post(post_write_hook("src/app.py"), store)
        state = store.load()
        assert state["plan_written"] is False


# ---------------------------------------------------------------------------
# PostToolUse: report archiving and completion
# ---------------------------------------------------------------------------

class TestReportPost:
    def test_report_write_sets_report_written_and_completes(self, tmp_state_file):
        write_state(tmp_state_file, make_state("report"))
        store = StateStore(tmp_state_file)
        write_guard.handle_post(post_write_hook(".claude/reports/latest-report.md"), store)
        state = store.load()
        assert state["report_written"] is True
        assert state["phase"] == "completed"
