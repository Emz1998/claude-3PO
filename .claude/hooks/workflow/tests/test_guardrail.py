"""Tests for guardrail.py, guards/phase_guard.py, guards/agent_guard.py, guards/review_guard.py."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
GUARDRAIL = WORKFLOW_DIR / "guardrail.py"

sys.path.insert(0, str(WORKFLOW_DIR.parent))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_state(phases_override=None, tdd=False, review_override=None):
    phases = [
        {"name": "explore",     "status": "pending", "agents": [], "files_created": []},
        {"name": "decision",    "status": "pending", "agents": [], "files_created": []},
        {"name": "plan",        "status": "pending", "agents": [], "files_created": []},
        {"name": "write-tests", "status": "pending", "agents": [], "files_created": []},
        {"name": "write-code",  "status": "pending", "agents": [], "files_created": []},
        {"name": "validate",    "status": "pending", "agents": [], "files_created": []},
        {"name": "pr-create",   "status": "pending", "agents": [], "files_created": []},
    ]
    if phases_override:
        for phase in phases:
            if phase["name"] in phases_override:
                phase.update(phases_override[phase["name"]])
    review = {
        "plan":  {"status": None, "iteration": 0, "max_iterations": 3, "scores": {"confidence": None, "quality": None}, "threshold": {"confidence": 80, "quality": 80}},
        "tests": {"status": None, "iteration": 0, "max_iterations": 3, "scores": {"confidence": None, "quality": None}, "threshold": {"confidence": 80, "quality": 80}},
    }
    if review_override:
        for key, val in review_override.items():
            review[key].update(val)
    return {
        "workflow_active": True,
        "workflow_type": None,
        "session_id": None,
        "story_id": None,
        "TDD": tdd,
        "phases": phases,
        "ci": {"status": "inactive"},
        "review": review,
        "task_manager_completed": True,
    }


@pytest.fixture
def state_file(tmp_path):
    f = tmp_path / "state.json"
    f.write_text(json.dumps(make_state()))
    return f


def pre_tool_agent(subagent_type, tool_use_id="t1"):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": subagent_type, "description": "x", "prompt": "x"},
        "tool_use_id": tool_use_id,
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def pre_tool_skill(skill_name):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": skill_name, "args": ""},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def subagent_stop(agent_type, last_message="Done.", agent_id="a1"):
    return {
        "hook_event_name": "SubagentStop",
        "agent_type": agent_type,
        "agent_id": agent_id,
        "last_assistant_message": last_message,
        "session_id": "s", "transcript_path": "t", "cwd": ".",
        "permission_mode": "default", "stop_hook_active": False,
        "agent_transcript_path": "x.jsonl",
    }


def stop_event(stop_hook_active=False):
    return {
        "hook_event_name": "Stop",
        "session_id": "s", "transcript_path": "t", "cwd": ".",
        "permission_mode": "default", "stop_hook_active": stop_hook_active,
    }


def pre_tool_write(file_path):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "x"},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def pre_tool_edit(file_path):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path, "old_string": "a", "new_string": "b"},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def pre_tool_bash(command):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command, "description": "x"},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def all_phases_completed():
    return {name: {"status": "completed"} for name in [
        "explore", "decision", "plan",
        "write-tests", "write-code", "validate", "pr-create",
    ]}


# ---------------------------------------------------------------------------
# phase_guard tests
# ---------------------------------------------------------------------------

class TestPhaseGuard:
    def test_allow_explore_first(self, state_file):
        from workflow.guards.phase_guard import validate
        result, _ = validate(pre_tool_skill("explore"), state_file)
        assert result == "allow"

    def test_block_wrong_first_skill(self, state_file):
        from workflow.guards.phase_guard import validate
        result, reason = validate(pre_tool_skill("decision"), state_file)
        assert result == "block"
        assert "explore" in reason

    def test_allow_decision_after_explore_complete(self, tmp_path):
        from workflow.guards.phase_guard import validate
        state = make_state({"explore": {"status": "completed"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_skill("decision"), f)
        assert result == "allow"

    def test_block_skipping_phase(self, tmp_path):
        from workflow.guards.phase_guard import validate
        state = make_state({"explore": {"status": "completed"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, reason = validate(pre_tool_skill("plan"), f)
        assert result == "block"
        assert "decision" in reason

    def test_sets_phase_in_progress_on_allow(self, state_file):
        from workflow.guards.phase_guard import validate
        validate(pre_tool_skill("explore"), state_file)
        state = json.loads(state_file.read_text())
        phase = next(p for p in state["phases"] if p["name"] == "explore")
        assert phase["status"] == "in_progress"

    def test_unknown_skill_is_allowed(self, state_file):
        from workflow.guards.phase_guard import validate
        result, _ = validate(pre_tool_skill("some-other-skill"), state_file)
        assert result == "allow"

    def test_allow_in_progress_phase_again(self, tmp_path):
        from workflow.guards.phase_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_skill("explore"), f)
        assert result == "allow"


# ---------------------------------------------------------------------------
# agent_guard tests
# ---------------------------------------------------------------------------

class TestAgentGuard:
    def test_allow_codebase_explorer_in_explore(self, tmp_path):
        from workflow.guards.agent_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_agent("codebase-explorer"), f)
        assert result == "allow"

    def test_allow_research_specialist_in_explore(self, tmp_path):
        from workflow.guards.agent_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_agent("research-specialist"), f)
        assert result == "allow"

    def test_block_wrong_agent_for_phase(self, tmp_path):
        from workflow.guards.agent_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, reason = validate(pre_tool_agent("qa-expert"), f)
        assert result == "block"
        assert "qa-expert" in reason

    def test_block_over_max_count_explorer(self, tmp_path):
        from workflow.guards.agent_guard import validate
        agents = [{"agent_type": "codebase-explorer", "status": "running", "tool_use_id": f"t{i}"} for i in range(3)]
        state = make_state({"explore": {"status": "in_progress", "agents": agents}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, reason = validate(pre_tool_agent("codebase-explorer"), f)
        assert result == "block"
        assert "max" in reason.lower()

    def test_block_over_max_count_researcher(self, tmp_path):
        from workflow.guards.agent_guard import validate
        agents = [{"agent_type": "research-specialist", "status": "running", "tool_use_id": f"t{i}"} for i in range(2)]
        state = make_state({"explore": {"status": "in_progress", "agents": agents}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, reason = validate(pre_tool_agent("research-specialist"), f)
        assert result == "block"
        assert "max" in reason.lower()

    def test_allow_up_to_max_count(self, tmp_path):
        from workflow.guards.agent_guard import validate
        agents = [{"agent_type": "codebase-explorer", "status": "completed", "tool_use_id": f"t{i}"} for i in range(2)]
        state = make_state({"explore": {"status": "in_progress", "agents": agents}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_agent("codebase-explorer"), f)
        assert result == "allow"

    def test_block_reviewer_before_primary_agent(self, tmp_path):
        from workflow.guards.agent_guard import validate
        state = make_state({"plan": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, reason = validate(pre_tool_agent("plan-reviewer"), f)
        assert result == "block"
        assert "plan-specialist" in reason

    def test_allow_reviewer_after_primary_agent(self, tmp_path):
        from workflow.guards.agent_guard import validate
        agents = [{"agent_type": "plan-specialist", "status": "completed", "tool_use_id": "t1"}]
        state = make_state({"plan": {"status": "in_progress", "agents": agents}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_agent("plan-reviewer"), f)
        assert result == "allow"

    def test_block_write_tests_if_tdd_false(self, tmp_path):
        from workflow.guards.agent_guard import validate
        state = make_state({"write-tests": {"status": "in_progress"}}, tdd=False)
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, reason = validate(pre_tool_agent("test-engineer"), f)
        assert result == "block"
        assert "TDD" in reason

    def test_allow_write_tests_if_tdd_true(self, tmp_path):
        from workflow.guards.agent_guard import validate
        state = make_state({"write-tests": {"status": "in_progress"}}, tdd=True)
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_agent("test-engineer"), f)
        assert result == "allow"

    def test_block_any_agent_in_write_code_phase(self, tmp_path):
        from workflow.guards.agent_guard import validate
        state = make_state({"write-code": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, reason = validate(pre_tool_agent("codebase-explorer"), f)
        assert result == "block"
        assert "write-code" in reason

    def test_no_active_phase_blocks(self, state_file):
        from workflow.guards.agent_guard import validate
        result, reason = validate(pre_tool_agent("codebase-explorer"), state_file)
        assert result == "block"
        assert "phase" in reason.lower()

    def test_records_running_agent_on_allow(self, tmp_path):
        from workflow.guards.agent_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        validate(pre_tool_agent("codebase-explorer", tool_use_id="tx1"), f)
        updated = json.loads(f.read_text())
        phase = next(p for p in updated["phases"] if p["name"] == "explore")
        assert any(a["agent_type"] == "codebase-explorer" and a["tool_use_id"] == "tx1" for a in phase["agents"])

    def test_block_plan_specialist_when_review_not_done(self, tmp_path):
        """plan-specialist blocked when plan-reviewer has reviewed (completed_consultants == completed_reviewers)
        and iteration is at max."""
        from workflow.guards.agent_guard import validate
        agents = [
            {"agent_type": "plan-specialist", "status": "completed", "tool_use_id": "t1"},
            {"agent_type": "plan-reviewer",   "status": "completed", "tool_use_id": "t2"},
            {"agent_type": "plan-specialist", "status": "completed", "tool_use_id": "t3"},
            {"agent_type": "plan-reviewer",   "status": "completed", "tool_use_id": "t4"},
            {"agent_type": "plan-specialist", "status": "completed", "tool_use_id": "t5"},
            {"agent_type": "plan-reviewer",   "status": "completed", "tool_use_id": "t6"},
        ]
        state = make_state({"plan": {"status": "in_progress", "agents": agents}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, reason = validate(pre_tool_agent("plan-specialist"), f)
        assert result == "block"
        assert "max" in reason.lower() or "iteration" in reason.lower()


# ---------------------------------------------------------------------------
# review_guard tests
# ---------------------------------------------------------------------------

class TestReviewGuard:
    def test_marks_agent_completed(self, tmp_path):
        from workflow.guards.review_guard import handle
        agents = [{"agent_type": "codebase-explorer", "status": "running", "tool_use_id": "t1"}]
        state = make_state({"explore": {"status": "in_progress", "agents": agents}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        handle(subagent_stop("codebase-explorer"), f)
        updated = json.loads(f.read_text())
        phase = next(p for p in updated["phases"] if p["name"] == "explore")
        assert any(a["status"] == "completed" for a in phase["agents"])

    def test_auto_advance_after_all_agents_done(self, tmp_path):
        from workflow.guards.review_guard import handle
        agents = [
            {"agent_type": "codebase-explorer",  "status": "completed", "tool_use_id": "t1"},
            {"agent_type": "codebase-explorer",  "status": "completed", "tool_use_id": "t2"},
            {"agent_type": "codebase-explorer",  "status": "completed", "tool_use_id": "t3"},
            {"agent_type": "research-specialist", "status": "completed", "tool_use_id": "t4"},
            {"agent_type": "research-specialist", "status": "running",   "tool_use_id": "t5"},
        ]
        state = make_state({"explore": {"status": "in_progress", "agents": agents}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        handle(subagent_stop("research-specialist", agent_id="a5"), f)
        updated = json.loads(f.read_text())
        explore = next(p for p in updated["phases"] if p["name"] == "explore")
        decision = next(p for p in updated["phases"] if p["name"] == "decision")
        assert explore["status"] == "completed"
        assert decision["status"] == "in_progress"

    def test_parse_scores_and_approve(self, tmp_path):
        from workflow.guards.review_guard import handle
        agents = [
            {"agent_type": "plan-specialist", "status": "completed", "tool_use_id": "t1"},
            {"agent_type": "plan-reviewer",   "status": "running",   "tool_use_id": "t2"},
        ]
        state = make_state({"plan": {"status": "in_progress", "agents": agents}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        msg = "Confidence Score: 85\nQuality Score: 90"
        handle(subagent_stop("plan-reviewer", last_message=msg), f)
        updated = json.loads(f.read_text())
        assert updated["review"]["plan"]["status"] == "approved"
        assert updated["review"]["plan"]["scores"]["confidence"] == 85
        assert updated["review"]["plan"]["scores"]["quality"] == 90

    def test_plan_approved_advances_phase(self, tmp_path):
        from workflow.guards.review_guard import handle
        agents = [
            {"agent_type": "plan-specialist", "status": "completed", "tool_use_id": "t1"},
            {"agent_type": "plan-reviewer",   "status": "running",   "tool_use_id": "t2"},
        ]
        state = make_state({"plan": {"status": "in_progress", "agents": agents}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        handle(subagent_stop("plan-reviewer", last_message="Confidence: 90\nQuality: 85"), f)
        updated = json.loads(f.read_text())
        plan = next(p for p in updated["phases"] if p["name"] == "plan")
        write_tests = next(p for p in updated["phases"] if p["name"] == "write-tests")
        assert plan["status"] == "completed"
        assert write_tests["status"] == "in_progress"

    def test_parse_scores_revision_needed(self, tmp_path):
        from workflow.guards.review_guard import handle
        agents = [
            {"agent_type": "plan-specialist", "status": "completed", "tool_use_id": "t1"},
            {"agent_type": "plan-reviewer",   "status": "running",   "tool_use_id": "t2"},
        ]
        state = make_state({"plan": {"status": "in_progress", "agents": agents}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        msg = "Confidence Score: 60\nQuality Score: 70"
        handle(subagent_stop("plan-reviewer", last_message=msg), f)
        updated = json.loads(f.read_text())
        assert updated["review"]["plan"]["status"] == "revision_needed"
        assert updated["review"]["plan"]["iteration"] == 1
        plan = next(p for p in updated["phases"] if p["name"] == "plan")
        assert plan["status"] == "in_progress"

    def test_max_iterations_marks_phase_failed(self, tmp_path):
        from workflow.guards.review_guard import handle
        agents = [
            {"agent_type": "plan-specialist", "status": "completed", "tool_use_id": "t1"},
            {"agent_type": "plan-reviewer",   "status": "running",   "tool_use_id": "t2"},
        ]
        state = make_state(
            {"plan": {"status": "in_progress", "agents": agents}},
            review_override={"plan": {"iteration": 2, "max_iterations": 3}},
        )
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        msg = "Confidence Score: 50\nQuality Score: 50"
        handle(subagent_stop("plan-reviewer", last_message=msg), f)
        updated = json.loads(f.read_text())
        assert updated["review"]["plan"]["status"] == "max_iterations_reached"
        plan = next(p for p in updated["phases"] if p["name"] == "plan")
        assert plan["status"] == "failed"

    def test_parse_varied_score_formats(self, tmp_path):
        from workflow.guards.review_guard import parse_scores
        assert parse_scores("confidence = 85\nquality is 90") == {"confidence": 85, "quality": 90}
        assert parse_scores("Confidence Score: 75\nQuality score: 80") == {"confidence": 75, "quality": 80}
        assert parse_scores("CONFIDENCE SCORE = 88\nQUALITY SCORE = 92") == {"confidence": 88, "quality": 92}
        assert parse_scores("no scores here") == {"confidence": None, "quality": None}

    def test_always_returns_allow(self, tmp_path):
        from workflow.guards.review_guard import handle
        state = make_state({"explore": {"status": "in_progress",
            "agents": [{"agent_type": "codebase-explorer", "status": "running", "tool_use_id": "t1"}]}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        decision, _ = handle(subagent_stop("codebase-explorer"), f)
        assert decision == "allow"

    def test_test_review_approved_advances_to_write_code(self, tmp_path):
        from workflow.guards.review_guard import handle
        agents = [
            {"agent_type": "test-engineer",  "status": "completed", "tool_use_id": "t1"},
            {"agent_type": "test-reviewer",  "status": "running",   "tool_use_id": "t2"},
        ]
        state = make_state({"write-tests": {"status": "in_progress", "agents": agents}}, tdd=True)
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        handle(subagent_stop("test-reviewer", last_message="Confidence: 85\nQuality: 90"), f)
        updated = json.loads(f.read_text())
        wt = next(p for p in updated["phases"] if p["name"] == "write-tests")
        wc = next(p for p in updated["phases"] if p["name"] == "write-code")
        assert wt["status"] == "completed"
        assert wc["status"] == "in_progress"


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

class TestCLI:
    def _run(self, hook_input: dict, extra_args=None, state_file=None):
        args = [sys.executable, str(GUARDRAIL), "--hook-input", json.dumps(hook_input)]
        if extra_args:
            args.extend(extra_args)
        env = {}
        if state_file:
            import os
            env = {**os.environ, "GUARDRAIL_STATE_PATH": str(state_file)}
        return subprocess.run(args, capture_output=True, text=True, env=env or None)

    def test_allow_exits_zero(self, tmp_path):
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result = self._run(pre_tool_agent("codebase-explorer"), state_file=f)
        assert result.returncode == 0
        assert "allow" in result.stdout

    def test_block_exits_zero_stdout(self, tmp_path):
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result = self._run(pre_tool_agent("qa-expert"), state_file=f)
        assert result.returncode == 0
        assert "block" in result.stdout

    def test_reason_flag_shows_message(self, tmp_path):
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result = self._run(pre_tool_agent("qa-expert"), extra_args=["--reason"], state_file=f)
        assert result.returncode == 0
        assert "block," in result.stdout

    def test_non_agent_tool_is_allowed(self, tmp_path):
        state = make_state()
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        hook = {
            "hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": "ls", "description": "list"},
            "tool_use_id": "t1", "session_id": "s",
            "transcript_path": "t", "cwd": ".", "permission_mode": "default",
        }
        result = self._run(hook, state_file=f)
        assert result.returncode == 0

    def test_advance_flag(self, tmp_path):
        state = make_state()
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        import os
        env = {**os.environ, "GUARDRAIL_STATE_PATH": str(f)}
        result = subprocess.run(
            [sys.executable, str(GUARDRAIL), "--advance"],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0
        updated = json.loads(f.read_text())
        first = updated["phases"][0]
        assert first["status"] == "in_progress"

    def test_cli_stop_block(self, tmp_path):
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result = self._run(stop_event(), extra_args=["--reason"], state_file=f)
        assert result.returncode == 0
        assert "block," in result.stdout


# ---------------------------------------------------------------------------
# stop_guard tests
# ---------------------------------------------------------------------------

class TestStopGuard:
    def test_allow_when_workflow_inactive(self, tmp_path):
        from workflow.guards.stop_guard import validate
        state = make_state()
        state["workflow_active"] = False
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(stop_event(), f)
        assert result == "allow"

    def test_allow_when_all_phases_completed(self, tmp_path):
        from workflow.guards.stop_guard import validate
        state = make_state(all_phases_completed())
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(stop_event(), f)
        assert result == "allow"

    def test_block_when_phases_incomplete(self, tmp_path):
        from workflow.guards.stop_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(stop_event(), f)
        assert result == "block"

    def test_allow_when_stop_hook_active(self, tmp_path):
        from workflow.guards.stop_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(stop_event(stop_hook_active=True), f)
        assert result == "allow"

    def test_block_reason_lists_incomplete_phases(self, tmp_path):
        from workflow.guards.stop_guard import validate
        overrides = {
            "explore": {"status": "completed"},
        }
        state = make_state(overrides)
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        _, reason = validate(stop_event(), f)
        assert "decision" in reason
        assert "plan" in reason
        assert "explore" not in reason


# ---------------------------------------------------------------------------
# write_guard tests
# ---------------------------------------------------------------------------

class TestWriteGuard:
    def test_allow_non_code_file(self, tmp_path):
        from workflow.guards.write_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_write("/project/README.md"), f)
        assert result == "allow"

    def test_allow_when_workflow_inactive(self, tmp_path):
        from workflow.guards.write_guard import validate
        state = make_state()
        state["workflow_active"] = False
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_write("/project/main.py"), f)
        assert result == "allow"

    def test_block_code_before_plan(self, tmp_path):
        from workflow.guards.write_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, reason = validate(pre_tool_write("/project/main.py"), f)
        assert result == "block"
        assert "plan" in reason.lower()

    def test_allow_code_after_plan_no_tdd(self, tmp_path):
        from workflow.guards.write_guard import validate
        overrides = {
            "explore": {"status": "completed"},
            "decision": {"status": "completed"},
            "plan": {"status": "completed"},
            "write-code": {"status": "in_progress"},
        }
        state = make_state(overrides, tdd=False)
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_write("/project/main.py"), f)
        assert result == "allow"

    def test_block_code_before_tests_tdd(self, tmp_path):
        from workflow.guards.write_guard import validate
        overrides = {
            "explore": {"status": "completed"},
            "decision": {"status": "completed"},
            "plan": {"status": "completed"},
            "write-tests": {"status": "in_progress"},
        }
        state = make_state(overrides, tdd=True)
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, reason = validate(pre_tool_write("/project/main.py"), f)
        assert result == "block"
        assert "test" in reason.lower()

    def test_allow_code_after_tests_tdd(self, tmp_path):
        from workflow.guards.write_guard import validate
        overrides = {
            "explore": {"status": "completed"},
            "decision": {"status": "completed"},
            "plan": {"status": "completed"},
            "write-tests": {"status": "completed"},
            "write-code": {"status": "in_progress"},
        }
        state = make_state(overrides, tdd=True)
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_write("/project/main.py"), f)
        assert result == "allow"

    def test_allow_claude_dir_always(self, tmp_path):
        from workflow.guards.write_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_write("/project/.claude/hooks/hook.py"), f)
        assert result == "allow"


# ---------------------------------------------------------------------------
# bash_guard tests
# ---------------------------------------------------------------------------

class TestBashGuard:
    def test_allow_non_push_command(self, tmp_path):
        from workflow.guards.bash_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_bash("ls -la"), f)
        assert result == "allow"

    def test_allow_when_workflow_inactive(self, tmp_path):
        from workflow.guards.bash_guard import validate
        state = make_state()
        state["workflow_active"] = False
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_bash("git push"), f)
        assert result == "allow"

    def test_block_git_push_incomplete(self, tmp_path):
        from workflow.guards.bash_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, reason = validate(pre_tool_bash("git push origin main"), f)
        assert result == "block"
        assert "push" in reason.lower() or "phase" in reason.lower()

    def test_block_gh_pr_create_incomplete(self, tmp_path):
        from workflow.guards.bash_guard import validate
        state = make_state({"explore": {"status": "in_progress"}})
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, reason = validate(pre_tool_bash("gh pr create --title 'test'"), f)
        assert result == "block"

    def test_allow_git_push_all_completed(self, tmp_path):
        from workflow.guards.bash_guard import validate
        state = make_state(all_phases_completed())
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state))
        result, _ = validate(pre_tool_bash("git push origin main"), f)
        assert result == "allow"
