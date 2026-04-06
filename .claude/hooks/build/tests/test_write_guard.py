"""Tests for guards/write_guard.py (new unified version)."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from build import recorder
from build.guards import write_guard
from build.session_store import SessionStore


def make_state(phase: str, **kwargs) -> dict:
    return {
        "workflow_active": True,
        "workflow_type": kwargs.get("workflow_type", "implement"),
        "phase": phase,
        "tdd": kwargs.get("tdd", True),
        "plan": {
            "file_path": kwargs.get("plan_file", None),
            "written": kwargs.get("plan_written", False),
            "review": {"iteration": 0, "scores": None, "status": None},
        },
        "tests": {
            "file_paths": kwargs.get("test_files_created", []),
            "review_result": None,
            "executed": False,
        },
        "report_written": kwargs.get("report_written", False),
        "agents": [],
    }


def write_state(tmp_state_file, state: dict) -> None:
    SessionStore("s", tmp_state_file).save(state)


VALID_PLAN = (
    "# Plan\n\n"
    "## Context\nSome context\n\n"
    "## Approach\nSome approach\n\n"
    "## Files to Modify\n| File | Change |\n\n"
    "## Verification\nRun tests\n"
)


def write_hook(file_path: str, content: str = "x") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": content},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def edit_hook(file_path: str, old_string: str = "a", new_string: str = "b") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path, "old_string": old_string, "new_string": new_string},
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
        tmp_state_file.write_text("")
        store = SessionStore("s", tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# Write-plan / review phases
# ---------------------------------------------------------------------------

class TestWritePlanPhase:
    def test_plan_write_allowed_with_valid_template(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook(".claude/plans/my-plan.md", VALID_PLAN), store)
        assert decision == "allow"

    def test_plan_write_blocked_missing_sections(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = write_guard.validate_pre(write_hook(".claude/plans/my-plan.md", "# Just a title"), store)
        assert decision == "block"
        assert "Context" in reason
        assert "Verification" in reason

    def test_plan_write_blocked_partial_sections(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = SessionStore("s", tmp_state_file)
        partial = "## Context\nSome context\n## Approach\nSome approach\n"
        decision, reason = write_guard.validate_pre(write_hook(".claude/plans/my-plan.md", partial), store)
        assert decision == "block"
        assert "Files to Modify" in reason
        assert "Verification" in reason

    def test_plan_edit_allowed_with_valid_result(self, tmp_state_file, tmp_path):
        write_state(tmp_state_file, make_state("write-plan"))
        store = SessionStore("s", tmp_state_file)
        plan_dir = tmp_path / ".claude" / "plans"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "plan.md"
        plan_file.write_text(VALID_PLAN)
        decision, _ = write_guard.validate_pre(
            edit_hook(str(plan_file), "Some context", "Updated context"), store
        )
        assert decision == "allow"

    def test_plan_edit_blocked_if_removes_section(self, tmp_state_file, tmp_path):
        write_state(tmp_state_file, make_state("write-plan"))
        store = SessionStore("s", tmp_state_file)
        plan_dir = tmp_path / ".claude" / "plans"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "plan.md"
        plan_file.write_text(VALID_PLAN)
        decision, reason = write_guard.validate_pre(
            edit_hook(str(plan_file), "## Verification\nRun tests\n", ""), store
        )
        assert decision == "block"
        assert "Verification" in reason

    def test_code_write_blocked_in_write_plan(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "block"
        assert "plan" in reason.lower()

    def test_claude_config_write_blocked_in_write_plan(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook(".claude/settings.json"), store)
        assert decision == "block"

    def test_non_plan_file_blocked_in_write_plan(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("README.md"), store)
        assert decision == "block"


class TestReviewPhase:
    def test_plan_write_allowed_in_review(self, tmp_state_file):
        write_state(tmp_state_file, make_state("review", plan_written=True))
        store = SessionStore("s", tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook(".claude/plans/my-plan.md", VALID_PLAN), store)
        assert decision == "allow"

    def test_plan_write_blocked_in_review_missing_sections(self, tmp_state_file):
        write_state(tmp_state_file, make_state("review"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = write_guard.validate_pre(write_hook(".claude/plans/my-plan.md", "# Bad plan"), store)
        assert decision == "block"
        assert "missing" in reason.lower()

    def test_code_write_blocked_in_review(self, tmp_state_file):
        write_state(tmp_state_file, make_state("review"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "block"


# ---------------------------------------------------------------------------
# Write-tests phase
# ---------------------------------------------------------------------------

class TestWriteTestsPhase:
    def test_test_file_allowed_in_write_tests(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("tests/test_foo.py"), store)
        assert decision == "allow"

    def test_code_file_blocked_in_write_tests(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "block"
        assert "test" in reason.lower()

    def test_test_file_tracked_in_post(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = SessionStore("s", tmp_state_file)
        recorder.record_write(post_write_hook("tests/test_foo.py"), store)
        state = store.load()
        assert "tests/test_foo.py" in state["tests"]["file_paths"]

    def test_non_code_file_allowed_in_write_tests(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("package.json"), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# Write-code phase
# ---------------------------------------------------------------------------

class TestWriteCodePhase:
    def test_code_write_allowed_in_write_code(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "allow"

    def test_edit_allowed_in_write_code(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = write_guard.validate_pre(edit_hook("src/app.py"), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# Validate phase
# ---------------------------------------------------------------------------

class TestValidatePhase:
    def test_code_write_blocked_in_validate(self, tmp_state_file):
        write_state(tmp_state_file, make_state("validate"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "block"
        assert "validate" in reason.lower()


# ---------------------------------------------------------------------------
# Code-review phase — code write allowed for refactoring
# ---------------------------------------------------------------------------

class TestCodeReviewPhase:
    def test_code_write_allowed_in_code_review(self, tmp_state_file):
        write_state(tmp_state_file, make_state("code-review"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# Report phase
# ---------------------------------------------------------------------------

class TestReportPhase:
    def test_report_write_allowed_to_reports_dir(self, tmp_state_file):
        write_state(tmp_state_file, make_state("report"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = write_guard.validate_pre(write_hook(".claude/reports/latest-report.md"), store)
        assert decision == "allow"

    def test_code_write_blocked_in_report(self, tmp_state_file):
        write_state(tmp_state_file, make_state("report"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = write_guard.validate_pre(write_hook("src/app.py"), store)
        assert decision == "block"


# ---------------------------------------------------------------------------
# PostToolUse: plan file tracking
# ---------------------------------------------------------------------------

class TestPlanWritePost:
    def test_plan_write_to_plans_dir_sets_plan_written(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = SessionStore("s", tmp_state_file)
        recorder.record_write(post_write_hook(".claude/plans/my-plan.md"), store)
        state = store.load()
        assert state["plan"]["written"] is True
        assert state["plan"]["file_path"] == ".claude/plans/my-plan.md"
        assert state["phase"] == "review"

    def test_non_plan_write_does_not_set_plan_written(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        recorder.record_write(post_write_hook("src/app.py"), store)
        state = store.load()
        assert state["plan"]["written"] is False


# ---------------------------------------------------------------------------
# PostToolUse: report archiving and completion
# ---------------------------------------------------------------------------

class TestReportPost:
    def test_report_write_sets_report_written_and_completes(self, tmp_state_file):
        write_state(tmp_state_file, make_state("report"))
        store = SessionStore("s", tmp_state_file)
        recorder.record_write(post_write_hook(".claude/reports/latest-report.md"), store)
        state = store.load()
        assert state["report_written"] is True
        assert state["phase"] == "completed"
