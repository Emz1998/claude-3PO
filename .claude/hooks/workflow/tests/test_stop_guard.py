"""Tests for guards/stop_guard.py (new unified version)."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow.guards import stop_guard
from workflow.session_store import SessionStore


def make_state(phase: str, **kwargs) -> dict:
    return {
        "workflow_active": True,
        "workflow_type": kwargs.get("workflow_type", "implement"),
        "phase": phase,
        "tdd": kwargs.get("tdd", False),
        "test_run_executed": kwargs.get("test_run_executed", False),
        "validation_result": kwargs.get("validation_result", None),
        "pr_status": kwargs.get("pr_status", "pending"),
        "ci_check_executed": kwargs.get("ci_check_executed", False),
        "report_written": kwargs.get("report_written", False),
    }


def write_state(tmp_state_file, state: dict) -> None:
    SessionStore("s", tmp_state_file).save(state)


def stop_event(active: bool = False) -> dict:
    return {
        "hook_event_name": "Stop",
        "stop_hook_active": active,
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


# ---------------------------------------------------------------------------
# Bypass: stop_hook_active
# ---------------------------------------------------------------------------

class TestStopHookBypass:
    def test_stop_hook_active_bypasses_all_checks(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = stop_guard.validate(stop_event(active=True), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# Inactive workflow
# ---------------------------------------------------------------------------

class TestWorkflowInactive:
    def test_stop_allowed_when_workflow_inactive(self, tmp_state_file):
        tmp_state_file.write_text("")
        store = SessionStore("s", tmp_state_file)
        decision, _ = stop_guard.validate(stop_event(), store)
        assert decision == "allow"


# ---------------------------------------------------------------------------
# /plan workflow: allow stop after approved
# ---------------------------------------------------------------------------

class TestPlanWorkflow:
    def test_stop_allowed_after_present_plan_for_plan_workflow(self, tmp_state_file):
        write_state(tmp_state_file, make_state("present-plan", workflow_type="plan"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = stop_guard.validate(stop_event(), store)
        assert decision == "allow"

    def test_stop_blocked_before_approved_for_plan_workflow(self, tmp_state_file):
        write_state(tmp_state_file, make_state("review", workflow_type="plan"))
        store = SessionStore("s", tmp_state_file)
        decision, reason = stop_guard.validate(stop_event(), store)
        assert decision == "block"

    def test_stop_blocked_in_explore_for_plan_workflow(self, tmp_state_file):
        write_state(tmp_state_file, make_state("explore", workflow_type="plan"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = stop_guard.validate(stop_event(), store)
        assert decision == "block"


# ---------------------------------------------------------------------------
# /implement workflow: block unless completed
# ---------------------------------------------------------------------------

class TestImplementWorkflow:
    def test_stop_allowed_when_completed(self, tmp_state_file):
        write_state(tmp_state_file, make_state("completed"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = stop_guard.validate(stop_event(), store)
        assert decision == "allow"

    def test_stop_blocked_when_tests_not_run(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "write-code",
            tdd=True,
            test_run_executed=False,
            validation_result=None,
            pr_status="pending",
        ))
        store = SessionStore("s", tmp_state_file)
        decision, reason = stop_guard.validate(stop_event(), store)
        assert decision == "block"
        assert reason

    def test_stop_blocked_when_validation_not_passed(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "pr-create",
            tdd=False,
            validation_result=None,
            pr_status="pending",
        ))
        store = SessionStore("s", tmp_state_file)
        decision, reason = stop_guard.validate(stop_event(), store)
        assert decision == "block"
        assert "validation" in reason.lower()

    def test_stop_blocked_when_pr_not_created(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "ci-check",
            tdd=False,
            validation_result="Pass",
            pr_status="pending",
            ci_check_executed=False,
        ))
        store = SessionStore("s", tmp_state_file)
        decision, reason = stop_guard.validate(stop_event(), store)
        assert decision == "block"
        assert "pr" in reason.lower()

    def test_stop_blocked_when_ci_not_checked(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "ci-check",
            tdd=False,
            validation_result="Pass",
            pr_status="created",
            ci_check_executed=False,
            report_written=False,
        ))
        store = SessionStore("s", tmp_state_file)
        decision, reason = stop_guard.validate(stop_event(), store)
        assert decision == "block"
        assert "ci" in reason.lower()

    def test_stop_blocked_when_report_not_written(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "report",
            tdd=False,
            validation_result="Pass",
            pr_status="created",
            ci_check_executed=True,
            report_written=False,
        ))
        store = SessionStore("s", tmp_state_file)
        decision, reason = stop_guard.validate(stop_event(), store)
        assert decision == "block"
        assert "report" in reason.lower()

    def test_stop_blocked_in_write_code_with_all_pending(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-code"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = stop_guard.validate(stop_event(), store)
        assert decision == "block"
