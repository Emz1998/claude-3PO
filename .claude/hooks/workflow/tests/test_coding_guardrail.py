"""Tests for coding_guardrail.py."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
CODING_GUARDRAIL = WORKFLOW_DIR / "coding_guardrail.py"

sys.path.insert(0, str(WORKFLOW_DIR.parent))


def make_state(tdd: bool = True, coding_workflow: dict | None = None) -> dict:
    state = {
        "workflow_active": True,
        "workflow_type": "plan",
        "TDD": tdd,
        "plan_workflow": {
            "plan_workflow_active": True,
            "phase": "write",
            "instructions": "Implement feature",
            "agents": [],
            "plan_file": ".claude/plans/test-plan.md",
            "review": {"status": "approved"},
        },
    }
    if coding_workflow is not None:
        state["coding_workflow"] = coding_workflow
    return state


def make_coding_workflow(
    *,
    phase: str = "write-tests",
    tdd: bool = True,
    tests_status: str = "pending",
    tests_review_called: bool = False,
    tests_last_result: str | None = None,
    validation_status: str = "pending",
    validation_review_called: bool = False,
    validation_last_result: str | None = None,
    pr_status: str = "pending",
    implementation_status: str = "pending",
    agents: list[dict] | None = None,
) -> dict:
    return {
        "coding_workflow_active": True,
        "phase": phase,
        "TDD": tdd,
        "activated_by_exit_plan_mode": True,
        "review": {
            "tests": {
                "review_called": tests_review_called,
                "status": tests_status,
                "last_result": tests_last_result,
            },
            "validation": {
                "review_called": validation_review_called,
                "status": validation_status,
                "last_result": validation_last_result,
            },
        },
        "agents": agents or [],
        "tests": {"status": tests_status},
        "implementation": {"status": implementation_status},
        "pr": {"status": pr_status, "command": None},
    }


@pytest.fixture
def state_file(tmp_path):
    f = tmp_path / "state.json"
    f.write_text(json.dumps(make_state()))
    return f


def post_exit_plan_mode():
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "ExitPlanMode",
        "tool_input": {},
        "tool_response": {
            "plan": None,
            "isAgent": False,
            "filePath": "/home/emhar/.claude/plans/test-plan.md",
        },
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def pre_tool_agent(agent_type: str, tool_use_id: str = "t1"):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": agent_type, "description": "x", "prompt": "x"},
        "tool_use_id": tool_use_id,
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def subagent_stop(agent_type: str, last_message: str = "Pass"):
    return {
        "hook_event_name": "SubagentStop",
        "agent_type": agent_type,
        "agent_id": "a1",
        "last_assistant_message": last_message,
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
        "stop_hook_active": False,
        "agent_transcript_path": "x.jsonl",
    }


def pre_tool_write(file_path: str):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "x"},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def pre_tool_edit(file_path: str):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path, "old_string": "a", "new_string": "b"},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def pre_tool_bash(command: str):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command, "description": "x"},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def post_tool_bash(command: str):
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command, "description": "x"},
        "tool_response": {"stdout": "ok"},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def stop_event():
    return {
        "hook_event_name": "Stop",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
        "stop_hook_active": False,
    }


class TestDispatch:
    def test_initializes_coding_workflow_on_exit_plan_mode(self, state_file):
        from workflow.coding_guardrail import _dispatch

        decision, _ = _dispatch(post_exit_plan_mode(), state_file)

        assert decision == "allow"
        state = json.loads(state_file.read_text())
        assert state["coding_workflow"]["coding_workflow_active"] is True
        assert state["coding_workflow"]["phase"] == "write-tests"
        assert state["coding_workflow"]["TDD"] is True
        assert state["plan_workflow"]["phase"] == "write"

    def test_non_tdd_skips_to_write_code(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(make_state(tdd=False)))

        decision, _ = _dispatch(post_exit_plan_mode(), state_file)

        assert decision == "allow"
        state = json.loads(state_file.read_text())
        assert state["coding_workflow"]["phase"] == "write-code"
        assert state["coding_workflow"]["TDD"] is False

    def test_inert_before_exit_plan_mode(self, state_file):
        from workflow.coding_guardrail import _dispatch

        decision, _ = _dispatch(pre_tool_write("src/app.py"), state_file)

        assert decision == "allow"


class TestWriteGuard:
    def test_allows_test_file_write_in_write_tests(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(phase="write-tests", tests_status="pending")
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, _ = _dispatch(pre_tool_write("tests/test_app.py"), state_file)

        assert decision == "allow"
        updated = json.loads(state_file.read_text())
        assert updated["coding_workflow"]["tests"]["status"] == "created"

    def test_blocks_code_write_before_review_called(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(
                phase="write-tests",
                tests_status="created",
                tests_review_called=False,
            )
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, reason = _dispatch(pre_tool_write("src/app.py"), state_file)

        assert decision == "block"
        assert "TestReviewer" in reason

    def test_blocks_code_write_after_failed_review(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(
                phase="write-tests",
                tests_status="failing",
                tests_review_called=True,
                tests_last_result="Fail",
            )
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, reason = _dispatch(pre_tool_edit("src/app.py"), state_file)

        assert decision == "block"
        assert "Fail" in reason

    def test_allows_code_write_after_passed_review(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(
                phase="write-code",
                tests_status="approved",
                tests_review_called=True,
                tests_last_result="Pass",
            )
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, _ = _dispatch(pre_tool_write("src/app.py"), state_file)

        assert decision == "allow"


class TestAgentGuard:
    def test_allows_test_reviewer_in_test_phase(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(phase="write-tests", tests_status="created")
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, _ = _dispatch(pre_tool_agent("TestReviewer"), state_file)

        assert decision == "allow"

    def test_blocks_validator_before_validate_phase(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(phase="write-tests", tests_status="created")
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, reason = _dispatch(pre_tool_agent("Validator"), state_file)

        assert decision == "block"
        assert "validate" in reason.lower()


class TestSubagentStop:
    def test_test_reviewer_fail_keeps_workflow_blocked(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(
                phase="write-tests",
                tests_status="created",
                agents=[{"agent_type": "TestReviewer", "status": "running", "tool_use_id": "t1", "iteration": 1}],
            )
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, _ = _dispatch(subagent_stop("TestReviewer", "Fail"), state_file)

        assert decision == "allow"
        updated = json.loads(state_file.read_text())
        assert updated["coding_workflow"]["phase"] == "write-tests"
        assert updated["coding_workflow"]["review"]["tests"]["last_result"] == "Fail"
        assert updated["coding_workflow"]["tests"]["status"] == "failing"

    def test_test_reviewer_pass_advances_to_write_code(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(
                phase="write-tests",
                tests_status="created",
                agents=[{"agent_type": "TestReviewer", "status": "running", "tool_use_id": "t1", "iteration": 1}],
            )
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, _ = _dispatch(subagent_stop("TestReviewer", "Pass"), state_file)

        assert decision == "allow"
        updated = json.loads(state_file.read_text())
        assert updated["coding_workflow"]["phase"] == "write-code"
        assert updated["coding_workflow"]["tests"]["status"] == "approved"

    def test_validator_fail_returns_to_write_code(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(
                phase="validate",
                tests_status="approved",
                tests_review_called=True,
                tests_last_result="Pass",
                validation_status="under_review",
                agents=[{"agent_type": "Validator", "status": "running", "tool_use_id": "t1", "iteration": 1}],
            )
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, _ = _dispatch(subagent_stop("Validator", "Fail"), state_file)

        assert decision == "allow"
        updated = json.loads(state_file.read_text())
        assert updated["coding_workflow"]["phase"] == "write-code"
        assert updated["coding_workflow"]["review"]["validation"]["last_result"] == "Fail"

    def test_validator_pass_advances_to_pr_create(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(
                phase="validate",
                tests_status="approved",
                tests_review_called=True,
                tests_last_result="Pass",
                validation_status="under_review",
                agents=[{"agent_type": "Validator", "status": "running", "tool_use_id": "t1", "iteration": 1}],
            )
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, _ = _dispatch(subagent_stop("Validator", "Pass"), state_file)

        assert decision == "allow"
        updated = json.loads(state_file.read_text())
        assert updated["coding_workflow"]["phase"] == "pr-create"


class TestBashAndStop:
    def test_blocks_pr_creation_before_validation_passes(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(
                phase="write-code",
                tests_status="approved",
                tests_review_called=True,
                tests_last_result="Pass",
            )
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, reason = _dispatch(pre_tool_bash("gh pr create --fill"), state_file)

        assert decision == "block"
        assert "validation" in reason.lower()

    def test_post_bash_marks_pr_created(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(
                phase="pr-create",
                tests_status="approved",
                tests_review_called=True,
                tests_last_result="Pass",
                validation_status="approved",
                validation_review_called=True,
                validation_last_result="Pass",
            )
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, _ = _dispatch(post_tool_bash("gh pr create --fill"), state_file)

        assert decision == "allow"
        updated = json.loads(state_file.read_text())
        assert updated["coding_workflow"]["pr"]["status"] == "created"
        assert updated["coding_workflow"]["phase"] == "completed"

    def test_stop_blocked_before_test_review_called(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(phase="write-tests", tests_status="created")
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, reason = _dispatch(stop_event(), state_file)

        assert decision == "block"
        assert "test review" in reason.lower()

    def test_stop_blocked_when_tests_are_failing(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(
                phase="write-tests",
                tests_status="failing",
                tests_review_called=True,
                tests_last_result="Fail",
            )
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, reason = _dispatch(stop_event(), state_file)

        assert decision == "block"
        assert "tests" in reason.lower()

    def test_stop_blocked_when_validation_failing(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(
                phase="write-code",
                tests_status="approved",
                tests_review_called=True,
                tests_last_result="Pass",
                validation_status="failing",
                validation_review_called=True,
                validation_last_result="Fail",
            )
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, reason = _dispatch(stop_event(), state_file)

        assert decision == "block"
        assert "validation" in reason.lower()

    def test_stop_allowed_once_everything_complete(self, tmp_path):
        from workflow.coding_guardrail import _dispatch

        state = make_state(
            coding_workflow=make_coding_workflow(
                phase="completed",
                tests_status="approved",
                tests_review_called=True,
                tests_last_result="Pass",
                validation_status="approved",
                validation_review_called=True,
                validation_last_result="Pass",
                pr_status="created",
                implementation_status="completed",
            )
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))

        decision, _ = _dispatch(stop_event(), state_file)

        assert decision == "allow"


class TestCli:
    def test_cli_blocks_with_reason(self, tmp_path):
        state = make_state(
            coding_workflow=make_coding_workflow(phase="write-tests", tests_status="created")
        )
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))
        env = {**os.environ, "CODING_GUARDRAIL_STATE_PATH": str(state_file)}

        result = subprocess.run(
            [sys.executable, str(CODING_GUARDRAIL), "--hook-input", json.dumps(stop_event()), "--reason"],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert result.stdout.strip().startswith("block,")
