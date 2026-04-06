"""Tests for guards/stop_guard.py — build version."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from build.guards import stop_guard
from build.session_store import SessionStore


def make_state(phase: str, **kwargs) -> dict:
    return {
        "workflow_active": True,
        "workflow_type": kwargs.get("workflow_type", "build"),
        "phase": phase,
        "tdd": kwargs.get("tdd", False),
        "tests": {
            "file_paths": [],
            "review_result": None,
            "executed": kwargs.get("test_executed", False),
        },
        "validation_result": kwargs.get("validation_result", None),
        "code_review": kwargs.get("code_review", {"iteration": 0, "scores": None, "status": None}),
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
# /build workflow: block unless completed
# ---------------------------------------------------------------------------

class TestBuildWorkflow:
    def test_stop_allowed_when_completed(self, tmp_state_file):
        write_state(tmp_state_file, make_state("completed"))
        store = SessionStore("s", tmp_state_file)
        decision, _ = stop_guard.validate(stop_event(), store)
        assert decision == "allow"

    def test_stop_blocked_when_tests_not_run(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "write-code",
            tdd=True,
            test_executed=False,
            validation_result=None,
        ))
        store = SessionStore("s", tmp_state_file)
        decision, reason = stop_guard.validate(stop_event(), store)
        assert decision == "block"
        assert reason

    def test_stop_blocked_when_validation_not_passed(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "code-review",
            tdd=False,
            validation_result=None,
        ))
        store = SessionStore("s", tmp_state_file)
        decision, reason = stop_guard.validate(stop_event(), store)
        assert decision == "block"
        assert "validation" in reason.lower()

    def test_stop_blocked_when_code_review_not_done(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "report",
            tdd=False,
            validation_result="Pass",
            code_review={"iteration": 0, "scores": None, "status": None},
            report_written=False,
        ))
        store = SessionStore("s", tmp_state_file)
        decision, reason = stop_guard.validate(stop_event(), store)
        assert decision == "block"
        assert "code review" in reason.lower()

    def test_stop_blocked_when_report_not_written(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "report",
            tdd=False,
            validation_result="Pass",
            code_review={"iteration": 1, "scores": {"confidence": 85, "quality": 90}, "status": "approved"},
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
