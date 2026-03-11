#!/usr/bin/env python3
"""TDD tests for the validation loop hook system.

Tests decision_handler, decision_guard, and validation_loop modules
by running them as subprocesses (matching how Claude Code invokes hooks).
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
WORKFLOW_DIR = PROJECT_ROOT / ".claude" / "hooks" / "workflow"
STATE_PATH = WORKFLOW_DIR / "state.json"
CONFIG_PATH = WORKFLOW_DIR / "validation_config.yaml"

DECISION_HANDLER = WORKFLOW_DIR / "validation" / "decision_handler.py"
DECISION_GUARD = WORKFLOW_DIR / "validation" / "decision_guard.py"
VALIDATION_LOOP = WORKFLOW_DIR / "validation" / "validation_loop.py"


def read_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def write_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state))


def backup_state():
    """Backup and restore state.json around tests."""
    original = STATE_PATH.read_text() if STATE_PATH.exists() else None
    return original


def restore_state(original):
    if original is not None:
        STATE_PATH.write_text(original)
    elif STATE_PATH.exists():
        STATE_PATH.unlink()


def make_decision_input(args: str = "7 8") -> str:
    """Build a PreToolUse JSON payload for Skill(decision)."""
    return json.dumps({
        "session_id": "test-session",
        "transcript_path": "/tmp/test.jsonl",
        "cwd": str(PROJECT_ROOT),
        "permission_mode": "bypassPermissions",
        "hook_event_name": "PreToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": "decision", "args": args},
        "tool_use_id": "toolu_test123",
    })


def make_non_decision_skill_input(skill: str = "plan") -> str:
    """Build a PreToolUse JSON payload for a non-decision skill."""
    return json.dumps({
        "session_id": "test-session",
        "transcript_path": "/tmp/test.jsonl",
        "cwd": str(PROJECT_ROOT),
        "permission_mode": "bypassPermissions",
        "hook_event_name": "PreToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": skill, "args": ""},
        "tool_use_id": "toolu_test456",
    })


def make_subagent_stop_input(agent_type: str = "code-reviewer") -> str:
    return json.dumps({
        "session_id": "test-session",
        "transcript_path": "/tmp/test.jsonl",
        "cwd": str(PROJECT_ROOT),
        "permission_mode": "bypassPermissions",
        "hook_event_name": "SubagentStop",
        "stop_hook_active": False,
        "agent_id": "test-agent",
        "agent_transcript_path": "/tmp/agent-test.jsonl",
        "agent_type": agent_type,
    })


@pytest.fixture(autouse=True)
def preserve_state():
    """Backup state.json before each test, restore after."""
    original = backup_state()
    # Ensure clean state for test (the real state.json may have invalid JSON)
    write_state({})
    yield
    restore_state(original)


# ─── decision_handler.py tests ───────────────────────────────────────────────


class TestDecisionHandler:
    """Tests for decision_handler.py — PreToolUse hook for Skill(decision)."""

    def test_valid_scores_write_to_state(self):
        """Skill(decision) with '75 80' should write validation scores to state.json."""
        result = subprocess.run(
            [sys.executable, str(DECISION_HANDLER)],
            input=make_decision_input("75 80"),
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"stdout: {result.stdout}, stderr: {result.stderr}"
        state = read_state()
        assert state["validation"]["decision_invoked"] is True
        assert state["validation"]["confidence_score"] == 75
        assert state["validation"]["quality_score"] == 80

    def test_missing_args_blocks(self):
        """Skill(decision) with empty args should exit 2 (block)."""
        result = subprocess.run(
            [sys.executable, str(DECISION_HANDLER)],
            input=make_decision_input(""),
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 2
        assert "2 arguments" in result.stderr.lower() or "/decision" in result.stderr.lower()

    def test_one_arg_blocks(self):
        """Skill(decision) with only one arg should exit 2 (block)."""
        result = subprocess.run(
            [sys.executable, str(DECISION_HANDLER)],
            input=make_decision_input("7"),
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 2

    def test_non_integer_args_blocks(self):
        """Skill(decision) with non-integer args should exit 2 (block)."""
        result = subprocess.run(
            [sys.executable, str(DECISION_HANDLER)],
            input=make_decision_input("high good"),
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 2
        assert "integer" in result.stderr.lower()

    def test_out_of_range_blocks(self):
        """Skill(decision) with scores outside 1-100 should exit 2 (block)."""
        result = subprocess.run(
            [sys.executable, str(DECISION_HANDLER)],
            input=make_decision_input("0 101"),
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 2
        assert "between 1 and 100" in result.stderr.lower()

    def test_skips_non_decision_skill(self):
        """Should exit 0 (skip) for non-decision skills."""
        result = subprocess.run(
            [sys.executable, str(DECISION_HANDLER)],
            input=make_non_decision_skill_input("plan"),
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0

    def test_preserves_existing_state_keys(self):
        """decision_handler should merge into existing state, not overwrite."""
        write_state({"recent_phase": "explore", "recent_coding_phase": "plan"})
        result = subprocess.run(
            [sys.executable, str(DECISION_HANDLER)],
            input=make_decision_input("90 90"),
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        state = read_state()
        assert state["recent_phase"] == "explore"
        assert state["validation"]["confidence_score"] == 90


# ─── decision_guard.py tests ─────────────────────────────────────────────────


class TestDecisionGuard:
    """Tests for decision_guard.py — blocks stop if /decision not invoked."""

    def test_blocks_when_decision_not_invoked(self):
        """Should exit 2 (block) when decision_invoked is false."""
        write_state({"validation": {"decision_invoked": False}})
        stdin_json = make_subagent_stop_input()
        result = subprocess.run(
            [sys.executable, str(DECISION_GUARD)],
            input=stdin_json, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 2, f"Expected exit 2, got {result.returncode}. stdout: {result.stdout}"
        assert "/decision" in result.stderr.lower() or "decision" in result.stderr.lower()

    def test_blocks_when_no_validation_key(self):
        """Should exit 2 (block) when validation key is missing from state."""
        write_state({"recent_phase": "explore"})
        stdin_json = make_subagent_stop_input()
        result = subprocess.run(
            [sys.executable, str(DECISION_GUARD)],
            input=stdin_json, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 2

    def test_allows_when_decision_invoked(self):
        """Should exit 0 (allow) when decision_invoked is true."""
        write_state({"validation": {"decision_invoked": True, "confidence_score": 80, "quality_score": 80}})
        stdin_json = make_subagent_stop_input()
        result = subprocess.run(
            [sys.executable, str(DECISION_GUARD)],
            input=stdin_json, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}. stdout: {result.stdout}"


# ─── validation_loop.py tests ────────────────────────────────────────────────


class TestValidationLoop:
    """Tests for validation_loop.py — checks scores vs config thresholds."""

    def test_skips_non_reviewer_agent(self):
        """Should exit 0 (skip) for non-reviewer agent types."""
        stdin_json = make_subagent_stop_input(agent_type="general-purpose")
        result = subprocess.run(
            [sys.executable, str(VALIDATION_LOOP)],
            input=stdin_json, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0

    def test_allows_passing_confidence_score(self):
        """Should exit 0 when confidence >= threshold (default 70)."""
        write_state({
            "validation": {
                "decision_invoked": True,
                "confidence_score": 80,
                "quality_score": 80,
                "iteration_count": 0,
            }
        })
        stdin_json = make_subagent_stop_input(agent_type="code-reviewer")
        result = subprocess.run(
            [sys.executable, str(VALIDATION_LOOP)],
            input=stdin_json, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0

    def test_blocks_low_confidence_score(self):
        """Should exit 2 (block) when confidence < threshold."""
        write_state({
            "validation": {
                "decision_invoked": True,
                "confidence_score": 40,
                "quality_score": 80,
                "iteration_count": 0,
            }
        })
        stdin_json = make_subagent_stop_input(agent_type="code-reviewer")
        result = subprocess.run(
            [sys.executable, str(VALIDATION_LOOP)],
            input=stdin_json, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 2, f"Expected exit 2, got {result.returncode}"
        assert "threshold" in result.stderr.lower() or "re-review" in result.stderr.lower()

    def test_increments_iteration_count_on_block(self):
        """Should increment iteration_count in state when blocking."""
        write_state({
            "validation": {
                "decision_invoked": True,
                "confidence_score": 30,
                "quality_score": 80,
                "iteration_count": 0,
            }
        })
        stdin_json = make_subagent_stop_input(agent_type="test-reviewer")
        subprocess.run(
            [sys.executable, str(VALIDATION_LOOP)],
            input=stdin_json, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        state = read_state()
        assert state["validation"]["iteration_count"] == 1

    def test_resets_decision_invoked_on_block(self):
        """Should reset decision_invoked to false when blocking (force re-invocation)."""
        write_state({
            "validation": {
                "decision_invoked": True,
                "confidence_score": 30,
                "quality_score": 80,
                "iteration_count": 0,
            }
        })
        stdin_json = make_subagent_stop_input(agent_type="code-reviewer")
        subprocess.run(
            [sys.executable, str(VALIDATION_LOOP)],
            input=stdin_json, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        state = read_state()
        assert state["validation"]["decision_invoked"] is False

    def test_escalates_after_max_iterations(self):
        """Should allow stop but print escalation message after max iterations."""
        write_state({
            "validation": {
                "decision_invoked": True,
                "confidence_score": 30,
                "quality_score": 30,
                "iteration_count": 3,  # equals config.iteration_loop (default 3)
            }
        })
        stdin_json = make_subagent_stop_input(agent_type="code-reviewer")
        result = subprocess.run(
            [sys.executable, str(VALIDATION_LOOP)],
            input=stdin_json, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        # Should allow stop (exit 0) but with escalation message
        assert result.returncode == 0, f"Expected exit 0 (escalation), got {result.returncode}"
        assert "iteration exhausted" in result.stdout.lower()

    def test_preserves_validation_state_on_pass(self):
        """Validation state is NOT reset on pass — scores and flags remain."""
        write_state({
            "recent_phase": "explore",
            "validation": {
                "decision_invoked": True,
                "confidence_score": 90,
                "quality_score": 90,
                "iteration_count": 1,
            }
        })
        stdin_json = make_subagent_stop_input(agent_type="code-reviewer")
        subprocess.run(
            [sys.executable, str(VALIDATION_LOOP)],
            input=stdin_json, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        state = read_state()
        # Validation state is preserved (no reset on pass)
        val = state.get("validation", {})
        assert val.get("decision_invoked") is True
        assert val.get("confidence_score") == 90
        assert val.get("quality_score") == 90
        # Other state keys preserved
        assert state["recent_phase"] == "explore"

    def test_works_with_plan_reviewer_agent(self):
        """Should apply validation to plan-reviewer agent type."""
        write_state({
            "validation": {
                "decision_invoked": True,
                "confidence_score": 80,
                "quality_score": 80,
                "iteration_count": 0,
            }
        })
        stdin_json = make_subagent_stop_input(agent_type="plan-reviewer")
        result = subprocess.run(
            [sys.executable, str(VALIDATION_LOOP)],
            input=stdin_json, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0

    def test_block_message_includes_iteration_info(self):
        """Block message should include current iteration and max."""
        write_state({
            "validation": {
                "decision_invoked": True,
                "confidence_score": 20,
                "quality_score": 80,
                "iteration_count": 1,
            }
        })
        stdin_json = make_subagent_stop_input(agent_type="code-reviewer")
        result = subprocess.run(
            [sys.executable, str(VALIDATION_LOOP)],
            input=stdin_json, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 2
        # Should mention iteration count
        assert "2" in result.stderr and "3" in result.stderr
