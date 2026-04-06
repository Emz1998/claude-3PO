"""Integration tests for guardrail.py — unified dispatcher."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

import importlib.util

from build.session_store import SessionStore

GUARDRAIL_PATH = WORKFLOW_DIR / "guardrail.py"


def _load_guardrail():
    spec = importlib.util.spec_from_file_location("guardrail_unified", GUARDRAIL_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_state(phase: str, **kwargs) -> dict:
    base = {
        "workflow_active": True,
        "workflow_type": kwargs.get("workflow_type", "implement"),
        "phase": phase,
        "tdd": kwargs.get("tdd", False),
        "skip": [],
        "agents": [],
        "plan": {
            "file_path": kwargs.get("plan_file", None),
            "written": kwargs.get("plan_written", False),
            "review": {
                "iteration": 0,
                "scores": None,
                "status": kwargs.get("plan_review_status", None),
            },
        },
        "tests": {
            "file_paths": kwargs.get("test_files_created", []),
            "review_result": None,
            "executed": False,
        },
        "docs_to_read": None,
        "files_written": [],
        "validation_result": kwargs.get("validation_result", None),
        "pr_status": kwargs.get("pr_status", "pending"),
        "ci_status": "pending",
        "report_written": False,
        "story_id": kwargs.get("story_id", None),
    }
    return base


def write_state(tmp_state_file, state: dict) -> None:
    SessionStore("s", tmp_state_file).save(state)


# ---------------------------------------------------------------------------
# Dispatch routing tests
# ---------------------------------------------------------------------------

class TestDispatchRouting:
    def test_agent_pre_tool_use_routed(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("explore"))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "Explore", "description": "x", "prompt": "x", "run_in_background": False},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"

    def test_write_pre_tool_use_blocked_in_write_plan(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("write-plan"))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "src/app.py", "content": "x"},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"

    def test_bash_pr_blocked_outside_pr_create(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("write-code"))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "gh pr create"},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, reason = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"

    def test_subagent_stop_validator_valid_report_allowed(self, tmp_state_file):
        """SubagentStop allows QualityAssurance with valid report schema."""
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("validate", agents=[
            {"agent_type": "QualityAssurance", "status": "running", "tool_use_id": "t1"}
        ]))
        valid_report = (
            "## QA Report: Test\n\n### Criteria Checklist\n| # | Criterion | Verdict | Evidence |\n"
            "### Test Results\n- **Command**: pytest\n"
            "### Final Verdict: PASS\n\nPass"
        )
        hook_input = {
            "hook_event_name": "SubagentStop",
            "agent_type": "QualityAssurance",
            "last_assistant_message": valid_report,
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
            "stop_hook_active": False,
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"

    def test_subagent_stop_validator_missing_sections_blocked(self, tmp_state_file):
        """SubagentStop blocks QualityAssurance with missing report sections."""
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("validate", agents=[
            {"agent_type": "QualityAssurance", "status": "running", "tool_use_id": "t1"}
        ]))
        hook_input = {
            "hook_event_name": "SubagentStop",
            "agent_type": "QualityAssurance",
            "last_assistant_message": "Pass",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
            "stop_hook_active": False,
        }
        decision, reason = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"
        assert "missing required sections" in reason

    def test_subagent_stop_non_validator_always_allowed(self, tmp_state_file):
        """SubagentStop allows agents without a defined schema."""
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("explore"))
        hook_input = {
            "hook_event_name": "SubagentStop",
            "agent_type": "Explore",
            "last_assistant_message": "Found stuff.",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
            "stop_hook_active": False,
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"

    def test_stop_event_blocked_in_write_code(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("write-code"))
        hook_input = {
            "hook_event_name": "Stop",
            "stop_hook_active": False,
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"

    def test_task_create_pre_routed_to_task_guard(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("task-create", story_id="SK-123"))
        # Without metadata, task_guard blocks — proves routing works
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "TaskCreate",
            "tool_input": {"subject": "Implement login", "description": "..."},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, reason = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"
        assert "metadata" in reason.lower()

    def test_unknown_event_allowed(self, tmp_state_file):
        gm = _load_guardrail()
        tmp_state_file.write_text("")
        hook_input = {
            "hook_event_name": "UnknownEvent",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"

    def test_webfetch_blocked_for_unsafe_domain(self, tmp_state_file):
        gm = _load_guardrail()
        # Use a non-agent-gated phase so the phase gate doesn't intercept
        write_state(tmp_state_file, make_state("write-code"))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://evil.example.com"},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"


# ---------------------------------------------------------------------------
# Phase gate tests — main agent vs subagent
# ---------------------------------------------------------------------------

class TestPhaseGate:
    """Verify that agent-only phases block non-Agent tools from main agent,
    but allow subagent tool calls through."""

    @pytest.mark.parametrize("phase", ["explore", "plan"])
    def test_main_agent_write_blocked_in_agent_only_phase(self, tmp_state_file, phase):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state(phase))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "src/app.py", "content": "x"},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, reason = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"
        assert "Agent tool" in reason

    @pytest.mark.parametrize("phase", ["explore", "plan"])
    def test_main_agent_read_blocked_in_agent_only_phase(self, tmp_state_file, phase):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state(phase))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "src/app.py"},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"

    @pytest.mark.parametrize("phase", ["explore", "plan"])
    def test_main_agent_bash_blocked_in_agent_only_phase(self, tmp_state_file, phase):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state(phase))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"

    @pytest.mark.parametrize("phase", ["explore", "plan"])
    def test_main_agent_agent_tool_allowed_in_agent_only_phase(self, tmp_state_file, phase):
        """Agent tool passes phase gate (agent_guard handles type validation)."""
        gm = _load_guardrail()
        agents_for_phase = {"explore": "Explore", "plan": "Plan"}
        write_state(tmp_state_file, make_state(phase))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": agents_for_phase[phase], "description": "x", "prompt": "x", "run_in_background": False},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"

    @pytest.mark.parametrize("phase", ["explore", "plan"])
    def test_subagent_write_allowed_in_agent_only_phase(self, tmp_state_file, phase):
        """Subagent calls (with agent_id) bypass the phase gate."""
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state(phase))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "notes.md", "content": "x"},
            "tool_use_id": "t1",
            "agent_id": "sub123",
            "agent_type": "Explore",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"

    @pytest.mark.parametrize("phase", ["explore", "plan"])
    def test_subagent_read_allowed_in_agent_only_phase(self, tmp_state_file, phase):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state(phase))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "src/app.py"},
            "tool_use_id": "t1",
            "agent_id": "sub123",
            "agent_type": "Plan",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"

    def test_review_phase_blocks_bash_from_main_agent(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("review"))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"

    def test_review_phase_allows_write_from_main_agent(self, tmp_state_file):
        """Write passes phase gate in review — write_guard handles plan-file enforcement."""
        gm = _load_guardrail()
        VALID_PLAN = (
            "# Plan\n\n"
            "## Context\nSome context\n\n"
            "## Approach\nSome approach\n\n"
            "## Files to Modify\n| File | Change |\n\n"
            "## Verification\nRun tests\n"
        )
        write_state(tmp_state_file, make_state("review", plan_written=True))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": ".claude/plans/plan.md", "content": VALID_PLAN},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"

    def test_review_phase_blocks_non_plan_write_from_main_agent(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("review"))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "README.md", "content": "x"},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"

    def test_phase_gate_inactive_workflow_allows_everything(self, tmp_state_file):
        gm = _load_guardrail()
        tmp_state_file.write_text("")
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "src/app.py", "content": "x"},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"

    @pytest.mark.parametrize("phase", ["write-code", "write-tests", "write-plan", "ci-check"])
    def test_non_gated_phases_allow_tools_from_main_agent(self, tmp_state_file, phase):
        """Phases that are not agent-gated should let tools through to per-guard logic."""
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state(phase))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "src/app.py"},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        # These may be allowed or blocked by per-guard logic, but NOT by the phase gate
        # Just verify it didn't get the phase gate message
        if decision == "block":
            assert "only the Agent tool" not in _


# ---------------------------------------------------------------------------
# ExitPlanMode handling
# ---------------------------------------------------------------------------

class TestExitPlanMode:
    def test_exit_plan_mode_pre_blocked_outside_present_plan_phase(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("write-code", plan_written=True, plan_review_status="approved"))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "ExitPlanMode",
            "tool_input": {},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, reason = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"
        assert "present-plan" in reason

    def test_exit_plan_mode_pre_blocked_without_approved_plan(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("present-plan", plan_written=False, plan_review_status=None))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "ExitPlanMode",
            "tool_input": {},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, reason = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"

    def test_exit_plan_mode_post_returns_allow_without_recording(self, tmp_state_file):
        """PostToolUse ExitPlanMode recording is now handled by recorder.py."""
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("present-plan", workflow_type="implement", story_id="SK-123"))
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "ExitPlanMode",
            "tool_input": {},
            "tool_response": {},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"
        state = SessionStore("s", tmp_state_file).load()
        # Phase should NOT change — recording is done by recorder.py
        assert state["phase"] == "present-plan"
