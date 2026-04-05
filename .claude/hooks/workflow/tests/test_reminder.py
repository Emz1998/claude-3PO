"""Tests for reminder.py — phase-aware context injection."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow import reminder
from workflow.session_store import SessionStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state(phase: str, **kwargs) -> dict:
    return {
        "workflow_active": True,
        "workflow_type": kwargs.get("workflow_type", "implement"),
        "phase": phase,
        "plan": {
            "file_path": kwargs.get("plan_file", None),
            "written": kwargs.get("plan_written", False),
            "review": {
                "iteration": kwargs.get("plan_review_iteration", 0),
                "scores": kwargs.get("plan_review_scores", None),
                "status": kwargs.get("plan_review_status", None),
            },
        },
        "tests": {
            "file_paths": [],
            "review_result": kwargs.get("test_review_result", None),
            "executed": False,
        },
        "docs_to_read": kwargs.get("docs_to_read", None),
        "validation_result": kwargs.get("validation_result", None),
        "tdd": kwargs.get("tdd", False),
        "story_id": kwargs.get("story_id", None),
        "skip": kwargs.get("skip", []),
    }


def write_state(state_file, state: dict) -> None:
    SessionStore("s", state_file).save(state)


def post_tool_hook(tool_name: str = "Agent") -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": tool_name,
        "tool_input": {},
        "tool_use_id": "t1",
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
        "permission_mode": "default",
    }


def subagent_start_hook(agent_type: str) -> dict:
    return {
        "hook_event_name": "SubagentStart",
        "agent_type": agent_type,
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
    }


def subagent_stop_hook(agent_type: str, last_message: str = "") -> dict:
    return {
        "hook_event_name": "SubagentStop",
        "agent_type": agent_type,
        "last_assistant_message": last_message,
        "session_id": "s",
        "transcript_path": "t",
        "cwd": ".",
    }


# ---------------------------------------------------------------------------
# Inactive workflow — no reminders
# ---------------------------------------------------------------------------

class TestWorkflowInactive:
    def test_post_tool_no_reminder_when_inactive(self, tmp_state_file):
        tmp_state_file.write_text("")
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook(), store)
        assert result is None

    def test_agent_start_no_reminder_when_inactive(self, tmp_state_file):
        tmp_state_file.write_text("")
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_agent_start_reminder(subagent_start_hook("Explore"), store)
        assert result is None

    def test_phase_transition_no_reminder_when_inactive(self, tmp_state_file):
        tmp_state_file.write_text("")
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(subagent_stop_hook("Explore"), store)
        assert result is None


# ---------------------------------------------------------------------------
# PostToolUse phase reminders
# ---------------------------------------------------------------------------

class TestPostToolReminders:
    def test_explore_kickoff_after_skill(self, tmp_state_file):
        write_state(tmp_state_file, make_state("explore"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook("Skill"), store)
        assert result is not None
        assert "EXPLORE" in result
        assert "3 Explore" in result
        assert "2 Research" in result

    def test_explore_remaining_after_agent_launch(self, tmp_state_file):
        state = make_state("explore")
        state["agents"] = [{"agent_type": "Explore", "status": "running", "tool_use_id": "t1"}]
        write_state(tmp_state_file, state)
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook("Agent"), store)
        assert result is not None
        assert "2 more Explore" in result
        assert "2 more Research" in result

    def test_explore_no_reminder_when_all_launched(self, tmp_state_file):
        state = make_state("explore")
        state["agents"] = (
            [{"agent_type": "Explore", "status": "running", "tool_use_id": f"e{i}"} for i in range(3)]
            + [{"agent_type": "Research", "status": "running", "tool_use_id": f"r{i}"} for i in range(2)]
        )
        write_state(tmp_state_file, state)
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook("Agent"), store)
        assert result is None

    def test_explore_no_reminder_on_generic_tool(self, tmp_state_file):
        write_state(tmp_state_file, make_state("explore"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook("Bash"), store)
        assert result is None

    def test_plan_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("plan"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook(), store)
        assert "PLAN" in result
        assert "Synthesize" in result

    def test_review_phase_with_iteration(self, tmp_state_file):
        write_state(tmp_state_file, make_state("review", plan_review_iteration=1))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook(), store)
        assert "REVIEW" in result
        assert "2/3" in result

    def test_write_tests_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook(), store)
        assert "WRITE-TESTS" in result
        assert "TDD" in result

    def test_write_code_phase_with_plan_files(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "write-code", docs_to_read=["src/app.py", "src/lib.py"],
        ))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook(), store)
        assert "WRITE-CODE" in result
        assert "src/app.py" in result
        assert "src/lib.py" in result

    def test_validate_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("validate"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook(), store)
        assert "VALIDATE" in result
        assert "pr-create" in result

    def test_no_reminder_for_unknown_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("completed"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook(), store)
        assert result is None

    def test_phase_reminder_fires_once(self, tmp_state_file):
        write_state(tmp_state_file, make_state("plan"))
        store = SessionStore("s", tmp_state_file)
        first = reminder.get_post_tool_reminder(post_tool_hook(), store)
        assert first is not None
        second = reminder.get_post_tool_reminder(post_tool_hook(), store)
        assert second is None

    def test_phase_reminder_resets_on_new_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("plan"))
        store = SessionStore("s", tmp_state_file)
        first = reminder.get_post_tool_reminder(post_tool_hook(), store)
        assert first is not None
        # Simulate phase advance
        store.set("phase", "write-plan")
        result = reminder.get_post_tool_reminder(post_tool_hook(), store)
        # write-plan has no PHASE_REMINDERS entry, but the key point is
        # the old phase reminder doesn't block new phases
        assert result is None  # write-plan has no reminder

    def test_explore_remaining_always_fires(self, tmp_state_file):
        """Explore remaining reminder fires every Agent launch (not deduped)."""
        state = make_state("explore")
        state["agents"] = [{"agent_type": "Explore", "status": "running", "tool_use_id": "t1"}]
        write_state(tmp_state_file, state)
        store = SessionStore("s", tmp_state_file)
        first = reminder.get_post_tool_reminder(post_tool_hook("Agent"), store)
        assert first is not None
        second = reminder.get_post_tool_reminder(post_tool_hook("Agent"), store)
        assert second is not None  # still fires


# ---------------------------------------------------------------------------
# PostToolUse ExitPlanMode reminders
# ---------------------------------------------------------------------------

class TestExitPlanModeReminders:
    def test_task_create_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("task-create"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook("ExitPlanMode"), store)
        assert "User approved" in result
        assert "TaskCreate" in result

    def test_write_tests_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook("ExitPlanMode"), store)
        assert "User approved" in result
        assert "TDD" in result

    def test_write_code_phase_with_files(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "write-code", docs_to_read=["src/main.py"],
        ))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook("ExitPlanMode"), store)
        assert "User approved" in result
        assert "src/main.py" in result

    def test_no_reminder_for_non_mapped_phase(self, tmp_state_file):
        write_state(tmp_state_file, make_state("present-plan"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_post_tool_reminder(post_tool_hook("ExitPlanMode"), store)
        assert result is None


# ---------------------------------------------------------------------------
# SubagentStart agent-role reminders
# ---------------------------------------------------------------------------

class TestAgentStartReminders:
    @pytest.mark.parametrize("agent_type,keyword", [
        ("Explore", "codebase structure"),
        ("Research", "external docs"),
        ("Plan", "Synthesize"),
        ("PlanReview", "confidence"),
        ("TestReviewer", "test coverage"),
        ("QualityAssurance", "passes tests"),
    ])
    def test_agent_reminders(self, agent_type, keyword, tmp_state_file):
        write_state(tmp_state_file, make_state("explore"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_agent_start_reminder(subagent_start_hook(agent_type), store)
        assert result is not None
        assert keyword in result

    def test_unknown_agent_no_reminder(self, tmp_state_file):
        write_state(tmp_state_file, make_state("explore"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_agent_start_reminder(subagent_start_hook("UnknownAgent"), store)
        assert result is None


# ---------------------------------------------------------------------------
# SubagentStop phase transition reminders
# ---------------------------------------------------------------------------

class TestPhaseTransitionReminders:
    def test_transition_to_plan(self, tmp_state_file):
        write_state(tmp_state_file, make_state("plan"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(subagent_stop_hook("Explore"), store)
        assert "Launch a Plan agent" in result

    def test_transition_to_write_plan(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-plan"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(subagent_stop_hook("Plan"), store)
        assert "Write it to .claude/plans/" in result

    def test_transition_to_present_plan(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "present-plan", plan_review_status="approved",
        ))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(subagent_stop_hook("PlanReview"), store)
        assert "ExitPlanMode" in result

    def test_transition_to_write_tests(self, tmp_state_file):
        write_state(tmp_state_file, make_state("write-tests"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(subagent_stop_hook("TaskManager"), store)
        assert "failing tests" in result

    def test_transition_to_write_code(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "write-code", docs_to_read=["a.py"],
        ))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(
            subagent_stop_hook("TestReviewer"), store,
        )
        assert "a.py" in result

    def test_transition_to_pr_create(self, tmp_state_file):
        write_state(tmp_state_file, make_state("pr-create", validation_result="Pass"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(subagent_stop_hook("QualityAssurance"), store)
        assert "gh pr create" in result

    def test_transition_to_ci_check(self, tmp_state_file):
        write_state(tmp_state_file, make_state("ci-check"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(subagent_stop_hook("QualityAssurance"), store)
        assert "gh pr checks" in result

    def test_transition_to_report(self, tmp_state_file):
        write_state(tmp_state_file, make_state("report"))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(subagent_stop_hook("QualityAssurance"), store)
        assert "completion report" in result

    def test_transition_reminder_fires_once(self, tmp_state_file):
        write_state(tmp_state_file, make_state("plan"))
        store = SessionStore("s", tmp_state_file)
        first = reminder.get_phase_transition_reminder(subagent_stop_hook("Explore"), store)
        assert first is not None
        second = reminder.get_phase_transition_reminder(subagent_stop_hook("Explore"), store)
        assert second is None


# ---------------------------------------------------------------------------
# SubagentStop failure reminders
# ---------------------------------------------------------------------------

class TestFailureReminders:
    def test_plan_review_revision_needed(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "review",
            plan_review_status="revision_needed",
            plan_review_scores={"confidence": 60, "quality": 70},
            plan_review_iteration=1,
        ))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(
            subagent_stop_hook("PlanReview"), store,
        )
        assert "FAILED" in result
        assert "confidence=60" in result
        assert "quality=70" in result
        assert "1/3" in result

    def test_plan_review_max_iterations(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "failed",
            plan_review_status="max_iterations_reached",
            plan_review_scores={"confidence": 50, "quality": 40},
            plan_review_iteration=3,
        ))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(
            subagent_stop_hook("PlanReview"), store,
        )
        assert "max iterations" in result
        assert "confidence=50" in result
        assert "quality=40" in result
        assert "ask the user" in result

    def test_test_review_fail(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "write-tests", test_review_result="Fail",
        ))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(
            subagent_stop_hook("TestReviewer"), store,
        )
        assert "Test review FAILED" in result

    def test_validator_fail(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "write-code", validation_result="Fail",
        ))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(
            subagent_stop_hook("QualityAssurance"), store,
        )
        assert "Validation FAILED" in result
        assert "write-code" in result

    def test_validator_pass_gives_transition_not_failure(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "pr-create", validation_result="Pass",
        ))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(
            subagent_stop_hook("QualityAssurance"), store,
        )
        assert "FAILED" not in result
        assert "gh pr create" in result

    def test_test_review_pass_gives_transition(self, tmp_state_file):
        write_state(tmp_state_file, make_state(
            "write-code",
            test_review_result="Pass",
            docs_to_read=["src/x.py"],
        ))
        store = SessionStore("s", tmp_state_file)
        result = reminder.get_phase_transition_reminder(
            subagent_stop_hook("TestReviewer"), store,
        )
        assert "FAILED" not in result
        assert "src/x.py" in result
