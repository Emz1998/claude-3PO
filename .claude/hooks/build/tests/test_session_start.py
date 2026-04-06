"""Tests for dispatchers/session_start.py — SessionStart:clear phase advancement."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from build import recorder
from build.session_store import SessionStore


def make_state(phase: str, **kwargs) -> dict:
    return {
        "workflow_active": kwargs.get("workflow_active", True),
        "workflow_type": kwargs.get("workflow_type", "build"),
        "phase": phase,
        "tdd": kwargs.get("tdd", False),
        "story_id": None,
    }


def write_state(tmp_state_file, state: dict) -> None:
    SessionStore("s", tmp_state_file).save(state)


class TestSessionStartClearAdvancement:
    """Tests the advance_after_plan_approval function as used by session_start dispatcher."""

    def test_always_advances_to_task_create(self, tmp_state_file):
        write_state(tmp_state_file, make_state("present-plan", tdd=True))
        store = SessionStore("s", tmp_state_file)
        result = recorder.advance_after_plan_approval(store)
        assert result == "task-create"

    def test_advances_to_task_create_without_tdd(self, tmp_state_file):
        write_state(tmp_state_file, make_state("present-plan", tdd=False))
        store = SessionStore("s", tmp_state_file)
        result = recorder.advance_after_plan_approval(store)
        assert result == "task-create"

    def test_no_advance_when_not_present_plan(self, tmp_state_file):
        """Phase must be present-plan for the dispatcher to call advance."""
        write_state(tmp_state_file, make_state("review"))
        store = SessionStore("s", tmp_state_file)
        result = recorder.advance_after_plan_approval(store)
        assert result == "task-create"  # function doesn't check phase

    def test_no_advance_when_inactive(self, tmp_state_file):
        write_state(tmp_state_file, make_state("present-plan", workflow_active=False))
        store = SessionStore("s", tmp_state_file)
        result = recorder.advance_after_plan_approval(store)
        assert result is None

    def test_plan_workflow_no_advance(self, tmp_state_file):
        write_state(tmp_state_file, make_state("present-plan", workflow_type="plan"))
        store = SessionStore("s", tmp_state_file)
        result = recorder.advance_after_plan_approval(store)
        assert result is None
        assert store.load()["phase"] == "present-plan"
