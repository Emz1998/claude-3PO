"""Integration tests for guardrail.py — unified dispatcher."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

import importlib.util

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
        "skip_explore": False,
        "skip_research": False,
        "agents": [],
        "plan_file": kwargs.get("plan_file", None),
        "plan_written": kwargs.get("plan_written", False),
        "plan_review_iteration": 0,
        "plan_review_scores": None,
        "plan_review_status": None,
        "tasks_created": 0,
        "test_files_created": kwargs.get("test_files_created", []),
        "test_review_result": None,
        "validation_result": kwargs.get("validation_result", None),
        "pr_status": kwargs.get("pr_status", "pending"),
        "ci_status": "pending",
        "ci_check_executed": False,
        "report_written": False,
        "story_id": kwargs.get("story_id", None),
    }
    return base


def write_state(tmp_state_file, state: dict) -> None:
    tmp_state_file.write_text(json.dumps(state))


# ---------------------------------------------------------------------------
# Dispatch routing tests
# ---------------------------------------------------------------------------

class TestDispatchRouting:
    def test_skill_post_activates_workflow(self, tmp_state_file):
        gm = _load_guardrail()
        tmp_state_file.write_text("{}")
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "plan", "args": ""},
            "tool_response": {"success": True},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"
        state = json.loads(tmp_state_file.read_text())
        assert state["workflow_active"] is True

    def test_agent_pre_tool_use_routed(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("explore"))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "Explore", "description": "x", "prompt": "x"},
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

    def test_subagent_stop_validator_advances_phase(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("validate", agents=[
            {"agent_type": "Validator", "status": "running", "tool_use_id": "t1"}
        ]))
        hook_input = {
            "hook_event_name": "SubagentStop",
            "agent_type": "Validator",
            "last_assistant_message": "Pass",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
            "stop_hook_active": False,
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"
        state = json.loads(tmp_state_file.read_text())
        assert state["phase"] == "pr-create"

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

    def test_user_prompt_submit_activates_workflow(self, tmp_state_file):
        gm = _load_guardrail()
        tmp_state_file.write_text("{}")
        hook_input = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "/plan --skip-all",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"
        state = json.loads(tmp_state_file.read_text())
        assert state["workflow_active"] is True

    def test_task_created_routed_to_task_guard(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("task-create", story_id="SK-123"))
        hook_input = {
            "hook_event_name": "TaskCreated",
            "task_id": "1",
            "task_subject": "SK-123: Implement login",
            "task_description": "...",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"

    def test_unknown_event_allowed(self, tmp_state_file):
        gm = _load_guardrail()
        tmp_state_file.write_text("{}")
        hook_input = {
            "hook_event_name": "UnknownEvent",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, _ = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "allow"

    def test_webfetch_blocked_for_unsafe_domain(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("explore"))
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
# ExitPlanMode handling
# ---------------------------------------------------------------------------

class TestExitPlanMode:
    def test_exit_plan_mode_pre_blocked_without_approved_plan(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("review", plan_written=False, plan_review_status=None))
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "ExitPlanMode",
            "tool_input": {},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        decision, reason = gm._dispatch(hook_input, tmp_state_file)
        assert decision == "block"

    def test_exit_plan_mode_post_advances_plan_workflow_to_approved(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("approved", workflow_type="plan"))
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

    def test_exit_plan_mode_post_advances_implement_to_task_create_with_story(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("approved", workflow_type="implement", story_id="SK-123"))
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "ExitPlanMode",
            "tool_input": {},
            "tool_response": {},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        gm._dispatch(hook_input, tmp_state_file)
        state = json.loads(tmp_state_file.read_text())
        assert state["phase"] == "task-create"

    def test_exit_plan_mode_post_skips_task_create_without_story_no_tdd(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("approved", workflow_type="implement", story_id=None, tdd=False))
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "ExitPlanMode",
            "tool_input": {},
            "tool_response": {},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        gm._dispatch(hook_input, tmp_state_file)
        state = json.loads(tmp_state_file.read_text())
        assert state["phase"] == "write-code"

    def test_exit_plan_mode_post_tdd_no_story_goes_to_write_tests(self, tmp_state_file):
        gm = _load_guardrail()
        write_state(tmp_state_file, make_state("approved", workflow_type="implement", story_id=None, tdd=True))
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "ExitPlanMode",
            "tool_input": {},
            "tool_response": {},
            "tool_use_id": "t1",
            "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        gm._dispatch(hook_input, tmp_state_file)
        state = json.loads(tmp_state_file.read_text())
        assert state["phase"] == "write-tests"
