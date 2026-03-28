"""Tests for plan_guardrail.py — plan workflow guardrail."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

# Import the module under test
import importlib.util

PLAN_GUARDRAIL = WORKFLOW_DIR / "plan_guardrail.py"


def _load_guardrail():
    spec = importlib.util.spec_from_file_location("plan_guardrail", PLAN_GUARDRAIL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def make_plan_state(
    phase="explore",
    skip=None,
    agents=None,
    plan_file=None,
    review=None,
):
    return {
        "plan_workflow_active": True,
        "phase": phase,
        "skip": skip or {"skip_explore": False, "skip_research": False},
        "agents": agents or [],
        "plan_file": plan_file,
        "review": review or {
            "iteration": 0,
            "max_iterations": 3,
            "threshold": {"confidence": 80, "quality": 80},
            "scores": None,
            "status": None,
        },
    }


def make_state_file(tmp_path, plan_state=None):
    f = tmp_path / "state.json"
    data = {}
    if plan_state is not None:
        data["workflow_active"] = True
        data["workflow_type"] = "plan"
        data["plan_workflow"] = plan_state
    f.write_text(json.dumps(data))
    return f


def skill_input(skill="plan", args=""):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": skill, "args": args},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def agent_input(subagent_type, tool_use_id="t1"):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": subagent_type, "description": "x", "prompt": "x"},
        "tool_use_id": tool_use_id,
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def webfetch_input(url):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "WebFetch",
        "tool_input": {"url": url},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def websearch_input(query, allowed_domains=None):
    ti = {"query": query}
    if allowed_domains is not None:
        ti["allowed_domains"] = allowed_domains
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "WebSearch",
        "tool_input": ti,
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def write_input(file_path):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "x"},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def exit_plan_mode_input():
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "ExitPlanMode",
        "tool_input": {},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def subagent_stop_input(agent_type, last_message="Done."):
    return {
        "hook_event_name": "SubagentStop",
        "agent_type": agent_type,
        "agent_id": "a1",
        "last_assistant_message": last_message,
        "session_id": "s", "transcript_path": "t", "cwd": ".",
        "permission_mode": "default", "stop_hook_active": False,
        "agent_transcript_path": "x.jsonl",
    }


VALID_PLAN_CONTENT = """# My Plan

## Context
This is why we need this change.

## Steps
### Step 1: Do the thing
Details here.

## Files to Modify
| File | Action |
|------|--------|
| `foo.py` | Create |

## Verification
Run tests.
"""

INVALID_PLAN_CONTENT = """# My Plan

## Steps
Do stuff.
"""


# ---------------------------------------------------------------------------
# TestSkipArgsParsing
# ---------------------------------------------------------------------------

class TestSkipArgsParsing:
    def setup_method(self):
        self.mod = _load_guardrail()

    def test_no_args_returns_no_skips(self):
        result = self.mod._parse_skip_args("")
        assert result == {"skip_explore": False, "skip_research": False}

    def test_skip_explore_flag(self):
        result = self.mod._parse_skip_args("--skip-explore")
        assert result["skip_explore"] is True
        assert result["skip_research"] is False

    def test_skip_research_flag(self):
        result = self.mod._parse_skip_args("--skip-research")
        assert result["skip_explore"] is False
        assert result["skip_research"] is True

    def test_skip_all_flag(self):
        result = self.mod._parse_skip_args("--skip-all")
        assert result["skip_explore"] is True
        assert result["skip_research"] is True

    def test_skip_flags_with_other_args(self):
        result = self.mod._parse_skip_args("--skip-explore --verbose")
        assert result["skip_explore"] is True
        assert result["skip_research"] is False


class TestInstructionsParsing:
    def setup_method(self):
        self.mod = _load_guardrail()

    def test_no_args_returns_empty_instructions(self):
        assert self.mod._parse_instructions("") == ""

    def test_instructions_only(self):
        assert self.mod._parse_instructions("Build a login feature") == "Build a login feature"

    def test_strips_skip_explore_flag(self):
        result = self.mod._parse_instructions("--skip-explore Build a login feature")
        assert result == "Build a login feature"

    def test_strips_skip_research_flag(self):
        result = self.mod._parse_instructions("--skip-research Refactor auth module")
        assert result == "Refactor auth module"

    def test_strips_skip_all_flag(self):
        result = self.mod._parse_instructions("--skip-all Add dark mode")
        assert result == "Add dark mode"

    def test_instructions_stored_in_state(self, tmp_path):
        state_file = make_state_file(tmp_path)
        mod = self.mod
        mod._dispatch(skill_input("plan", "--skip-explore Add dark mode support"), state_file)
        state = json.loads(state_file.read_text())
        assert state["plan_workflow"]["instructions"] == "Add dark mode support"

    def test_instructions_empty_when_only_flags(self, tmp_path):
        state_file = make_state_file(tmp_path)
        self.mod._dispatch(skill_input("plan", "--skip-all"), state_file)
        state = json.loads(state_file.read_text())
        assert state["plan_workflow"]["instructions"] == ""


# ---------------------------------------------------------------------------
# TestSkillInterception
# ---------------------------------------------------------------------------

class TestSkillInterception:
    def setup_method(self):
        self.mod = _load_guardrail()

    def test_allow_plan_skill_and_activate_workflow(self, tmp_path):
        state_file = make_state_file(tmp_path)
        decision, _ = self.mod._dispatch(skill_input("plan", ""), state_file)
        assert decision == "allow"
        state = json.loads(state_file.read_text())
        assert state["workflow_active"] is True
        assert state["workflow_type"] == "plan"
        assert state["plan_workflow"]["plan_workflow_active"] is True

    def test_ignore_non_plan_skills(self, tmp_path):
        state_file = make_state_file(tmp_path)
        decision, _ = self.mod._dispatch(skill_input("explore", ""), state_file)
        assert decision == "allow"
        state = json.loads(state_file.read_text())
        assert "plan_workflow" not in state


    def test_stores_skip_config_in_state(self, tmp_path):
        state_file = make_state_file(tmp_path)
        self.mod._dispatch(skill_input("plan", "--skip-explore"), state_file)
        state = json.loads(state_file.read_text())
        assert state["plan_workflow"]["skip"]["skip_explore"] is True
        assert state["plan_workflow"]["skip"]["skip_research"] is False


# ---------------------------------------------------------------------------
# TestAgentGuard
# ---------------------------------------------------------------------------

class TestAgentGuard:
    def setup_method(self):
        self.mod = _load_guardrail()

    def test_allow_explore_in_explore_phase(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        decision, _ = self.mod._dispatch(agent_input("Explore"), state_file)
        assert decision == "allow"

    def test_block_explore_in_background(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        inp = agent_input("Explore")
        inp["tool_input"]["run_in_background"] = True
        decision, reason = self.mod._dispatch(inp, state_file)
        assert decision == "block"
        assert "background" in reason.lower()

    def test_block_research_in_background(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        inp = agent_input("Research")
        inp["tool_input"]["run_in_background"] = True
        decision, reason = self.mod._dispatch(inp, state_file)
        assert decision == "block"
        assert "background" in reason.lower()

    def test_allow_research_in_explore_phase(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        decision, _ = self.mod._dispatch(agent_input("Research"), state_file)
        assert decision == "allow"

    def test_block_explore_over_max_3(self, tmp_path):
        agents = [
            {"agent_type": "Explore", "status": "running", "tool_use_id": "t1"},
            {"agent_type": "Explore", "status": "running", "tool_use_id": "t2"},
            {"agent_type": "Explore", "status": "running", "tool_use_id": "t3"},
        ]
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore", agents=agents))
        decision, reason = self.mod._dispatch(agent_input("Explore"), state_file)
        assert decision == "block"
        assert "max" in reason.lower() or "3" in reason

    def test_block_research_over_max_2(self, tmp_path):
        agents = [
            {"agent_type": "Research", "status": "running", "tool_use_id": "t1"},
            {"agent_type": "Research", "status": "running", "tool_use_id": "t2"},
        ]
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore", agents=agents))
        decision, reason = self.mod._dispatch(agent_input("Research"), state_file)
        assert decision == "block"
        assert "max" in reason.lower() or "2" in reason

    def test_block_plan_agent_before_explorers_done(self, tmp_path):
        # Only 1 Explore completed, need 3
        agents = [{"agent_type": "Explore", "status": "completed", "tool_use_id": "t1"}]
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore", agents=agents))
        decision, reason = self.mod._dispatch(agent_input("Plan"), state_file)
        assert decision == "block"

    def test_allow_plan_agent_after_all_required_agents_done(self, tmp_path):
        agents = [
            {"agent_type": "Explore", "status": "completed", "tool_use_id": "t1"},
            {"agent_type": "Explore", "status": "completed", "tool_use_id": "t2"},
            {"agent_type": "Explore", "status": "completed", "tool_use_id": "t3"},
            {"agent_type": "Research", "status": "completed", "tool_use_id": "t4"},
            {"agent_type": "Research", "status": "completed", "tool_use_id": "t5"},
        ]
        state_file = make_state_file(tmp_path, make_plan_state(phase="plan", agents=agents))
        decision, _ = self.mod._dispatch(agent_input("Plan"), state_file)
        assert decision == "allow"

    def test_allow_plan_agent_when_explore_skipped(self, tmp_path):
        agents = [
            {"agent_type": "Research", "status": "completed", "tool_use_id": "t1"},
            {"agent_type": "Research", "status": "completed", "tool_use_id": "t2"},
        ]
        skip = {"skip_explore": True, "skip_research": False}
        state_file = make_state_file(tmp_path, make_plan_state(phase="plan", skip=skip, agents=agents))
        decision, _ = self.mod._dispatch(agent_input("Plan"), state_file)
        assert decision == "allow"

    def test_allow_plan_agent_when_research_skipped(self, tmp_path):
        agents = [
            {"agent_type": "Explore", "status": "completed", "tool_use_id": "t1"},
            {"agent_type": "Explore", "status": "completed", "tool_use_id": "t2"},
            {"agent_type": "Explore", "status": "completed", "tool_use_id": "t3"},
        ]
        skip = {"skip_explore": False, "skip_research": True}
        state_file = make_state_file(tmp_path, make_plan_state(phase="plan", skip=skip, agents=agents))
        decision, _ = self.mod._dispatch(agent_input("Plan"), state_file)
        assert decision == "allow"

    def test_allow_plan_agent_when_all_skipped(self, tmp_path):
        skip = {"skip_explore": True, "skip_research": True}
        state_file = make_state_file(tmp_path, make_plan_state(phase="plan", skip=skip))
        decision, _ = self.mod._dispatch(agent_input("Plan"), state_file)
        assert decision == "allow"

    def test_allow_plan_review_in_review_phase(self, tmp_path):
        agents = [{"agent_type": "Plan", "status": "completed", "tool_use_id": "t1"}]
        state_file = make_state_file(tmp_path, make_plan_state(phase="review", agents=agents))
        decision, _ = self.mod._dispatch(agent_input("Plan-Review"), state_file)
        assert decision == "allow"

    def test_block_plan_review_before_review_phase(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="plan"))
        decision, reason = self.mod._dispatch(agent_input("Plan-Review"), state_file)
        assert decision == "block"

    def test_block_plan_review_over_max_iterations(self, tmp_path):
        agents = [
            {"agent_type": "Plan-Review", "status": "running", "tool_use_id": "t1"},
            {"agent_type": "Plan-Review", "status": "running", "tool_use_id": "t2"},
            {"agent_type": "Plan-Review", "status": "running", "tool_use_id": "t3"},
        ]
        state_file = make_state_file(tmp_path, make_plan_state(phase="review", agents=agents))
        decision, reason = self.mod._dispatch(agent_input("Plan-Review"), state_file)
        assert decision == "block"

    def test_allow_agent_when_workflow_not_active(self, tmp_path):
        state_file = make_state_file(tmp_path)  # no plan_workflow in state
        decision, _ = self.mod._dispatch(agent_input("codebase-explorer"), state_file)
        assert decision == "allow"

    def test_block_unknown_agent_type(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        decision, reason = self.mod._dispatch(agent_input("codebase-explorer"), state_file)
        assert decision == "block"
        assert "not allowed" in reason.lower() or "unknown" in reason.lower()


# ---------------------------------------------------------------------------
# TestWebFetchGuard
# ---------------------------------------------------------------------------

class TestWebFetchGuard:
    def setup_method(self):
        self.mod = _load_guardrail()

    def test_allow_safe_domain(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        decision, _ = self.mod._dispatch(webfetch_input("https://docs.anthropic.com/guide"), state_file)
        assert decision == "allow"

    def test_allow_subdomain_of_safe_domain(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        decision, _ = self.mod._dispatch(webfetch_input("https://sub.github.com/repo"), state_file)
        assert decision == "allow"

    def test_block_unsafe_domain(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        decision, reason = self.mod._dispatch(webfetch_input("https://malicious.example.com/page"), state_file)
        assert decision == "block"
        assert "domain" in reason.lower() or "not allowed" in reason.lower()

    def test_block_empty_url(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        decision, reason = self.mod._dispatch(webfetch_input(""), state_file)
        assert decision == "block"

    def test_block_malformed_url(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        decision, reason = self.mod._dispatch(webfetch_input("not-a-url"), state_file)
        assert decision == "block"


# ---------------------------------------------------------------------------
# TestWebSearchGuard
# ---------------------------------------------------------------------------

class TestWebSearchGuard:
    def setup_method(self):
        self.mod = _load_guardrail()

    def test_injects_allowed_domains(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        decision, _ = self.mod._dispatch(websearch_input("python async"), state_file)
        # Returns JSON string with updatedInput
        assert decision.startswith("{")
        data = json.loads(decision)
        assert "updatedInput" in data
        assert "allowed_domains" in data["updatedInput"]
        assert len(data["updatedInput"]["allowed_domains"]) > 0

    def test_preserves_original_query(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        decision, _ = self.mod._dispatch(websearch_input("react hooks"), state_file)
        data = json.loads(decision)
        assert data["updatedInput"]["query"] == "react hooks"

    def test_overrides_user_allowed_domains_with_safe_list(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore"))
        inp = websearch_input("query", allowed_domains=["evil.com"])
        decision, _ = self.mod._dispatch(inp, state_file)
        data = json.loads(decision)
        assert "evil.com" not in data["updatedInput"]["allowed_domains"]


# ---------------------------------------------------------------------------
# TestSubagentStop
# ---------------------------------------------------------------------------

class TestSubagentStop:
    def setup_method(self):
        self.mod = _load_guardrail()

    def test_marks_agent_completed(self, tmp_path):
        agents = [{"agent_type": "Explore", "status": "running", "tool_use_id": "t1"}]
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore", agents=agents))
        self.mod._dispatch(subagent_stop_input("Explore"), state_file)
        state = json.loads(state_file.read_text())
        pw = state["plan_workflow"]
        assert pw["agents"][0]["status"] == "completed"

    def test_unlocks_plan_phase_after_all_explore_done(self, tmp_path):
        agents = [
            {"agent_type": "Explore", "status": "completed", "tool_use_id": "t1"},
            {"agent_type": "Explore", "status": "completed", "tool_use_id": "t2"},
            {"agent_type": "Explore", "status": "running", "tool_use_id": "t3"},
            {"agent_type": "Research", "status": "completed", "tool_use_id": "t4"},
            {"agent_type": "Research", "status": "completed", "tool_use_id": "t5"},
        ]
        state_file = make_state_file(tmp_path, make_plan_state(phase="explore", agents=agents))
        self.mod._dispatch(subagent_stop_input("Explore"), state_file)
        state = json.loads(state_file.read_text())
        assert state["plan_workflow"]["phase"] == "plan"

    def test_transitions_to_review_after_plan_completion(self, tmp_path):
        agents = [{"agent_type": "Plan", "status": "running", "tool_use_id": "t1"}]
        state_file = make_state_file(tmp_path, make_plan_state(phase="plan", agents=agents))
        self.mod._dispatch(subagent_stop_input("Plan"), state_file)
        state = json.loads(state_file.read_text())
        assert state["plan_workflow"]["phase"] == "review"

    def test_review_pass_transitions_to_write(self, tmp_path):
        agents = [{"agent_type": "Plan-Review", "status": "running", "tool_use_id": "t1"}]
        state_file = make_state_file(tmp_path, make_plan_state(phase="review", agents=agents))
        msg = "The plan looks great. Confidence score: 90, Quality score: 85"
        self.mod._dispatch(subagent_stop_input("Plan-Review", msg), state_file)
        state = json.loads(state_file.read_text())
        assert state["plan_workflow"]["phase"] == "write"
        assert state["plan_workflow"]["review"]["status"] == "approved"

    def test_review_fail_triggers_revision(self, tmp_path):
        agents = [{"agent_type": "Plan-Review", "status": "running", "tool_use_id": "t1"}]
        state_file = make_state_file(tmp_path, make_plan_state(phase="review", agents=agents))
        msg = "Needs work. Confidence score: 60, Quality score: 55"
        self.mod._dispatch(subagent_stop_input("Plan-Review", msg), state_file)
        state = json.loads(state_file.read_text())
        assert state["plan_workflow"]["review"]["status"] == "revision_needed"
        assert state["plan_workflow"]["review"]["iteration"] == 1
        assert state["plan_workflow"]["phase"] == "review"

    def test_review_max_iterations_transitions_to_failed(self, tmp_path):
        agents = [{"agent_type": "Plan-Review", "status": "running", "tool_use_id": "t1"}]
        review = {
            "iteration": 2,
            "max_iterations": 3,
            "threshold": {"confidence": 80, "quality": 80},
            "scores": None,
            "status": "revision_needed",
        }
        state_file = make_state_file(tmp_path, make_plan_state(phase="review", agents=agents, review=review))
        msg = "Still not great. Confidence score: 50, Quality score: 50"
        self.mod._dispatch(subagent_stop_input("Plan-Review", msg), state_file)
        state = json.loads(state_file.read_text())
        assert state["plan_workflow"]["phase"] == "failed"
        assert state["plan_workflow"]["review"]["status"] == "max_iterations_reached"

    def test_review_parses_confidence_and_quality_scores(self, tmp_path):
        agents = [{"agent_type": "Plan-Review", "status": "running", "tool_use_id": "t1"}]
        state_file = make_state_file(tmp_path, make_plan_state(phase="review", agents=agents))
        msg = "Confidence score is 92 and quality score is 88."
        self.mod._dispatch(subagent_stop_input("Plan-Review", msg), state_file)
        state = json.loads(state_file.read_text())
        scores = state["plan_workflow"]["review"]["scores"]
        assert scores["confidence"] == 92
        assert scores["quality"] == 88


# ---------------------------------------------------------------------------
# TestWriteGuard
# ---------------------------------------------------------------------------

class TestWriteGuard:
    def setup_method(self):
        self.mod = _load_guardrail()

    def test_allow_write_to_plans_dir(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="write"))
        decision, _ = self.mod._dispatch(write_input(".claude/plans/my-plan.md"), state_file)
        assert decision == "allow"

    def test_block_write_outside_plans_dir(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="write"))
        decision, reason = self.mod._dispatch(write_input("src/app.py"), state_file)
        assert decision == "block"
        assert ".claude/plans" in reason or "plans" in reason.lower()

    def test_record_plan_file_path_in_state(self, tmp_path):
        state_file = make_state_file(tmp_path, make_plan_state(phase="write"))
        self.mod._dispatch(write_input(".claude/plans/my-plan.md"), state_file)
        state = json.loads(state_file.read_text())
        assert state["plan_workflow"]["plan_file"] == ".claude/plans/my-plan.md"


# ---------------------------------------------------------------------------
# TestPlanTemplateValidation
# ---------------------------------------------------------------------------

class TestPlanTemplateValidation:
    def setup_method(self):
        self.mod = _load_guardrail()

    def test_valid_plan_passes(self):
        passed, missing = self.mod._validate_plan_template(VALID_PLAN_CONTENT)
        assert passed is True
        assert missing == []

    def test_missing_context_section_fails(self):
        content = VALID_PLAN_CONTENT.replace("## Context\n", "")
        passed, missing = self.mod._validate_plan_template(content)
        assert passed is False
        assert any("Context" in m for m in missing)

    def test_missing_verification_section_fails(self):
        content = VALID_PLAN_CONTENT.replace("## Verification\n", "")
        passed, missing = self.mod._validate_plan_template(content)
        assert passed is False
        assert any("Verification" in m for m in missing)

    def test_missing_files_section_fails(self):
        content = VALID_PLAN_CONTENT.replace("## Files to Modify\n", "")
        passed, missing = self.mod._validate_plan_template(content)
        assert passed is False

    def test_accepts_critical_files_as_alternative(self):
        content = VALID_PLAN_CONTENT.replace("## Files to Modify", "## Critical Files")
        passed, missing = self.mod._validate_plan_template(content)
        assert passed is True

    def test_accepts_steps_as_alternative_to_approach(self):
        # VALID_PLAN_CONTENT already uses Steps — confirm it passes
        passed, missing = self.mod._validate_plan_template(VALID_PLAN_CONTENT)
        assert passed is True

    def test_empty_plan_fails(self):
        passed, missing = self.mod._validate_plan_template("")
        assert passed is False
        assert len(missing) > 0

    def test_block_reason_lists_missing_sections(self):
        passed, missing = self.mod._validate_plan_template(INVALID_PLAN_CONTENT)
        assert passed is False
        assert len(missing) >= 2


# ---------------------------------------------------------------------------
# TestExitPlanMode
# ---------------------------------------------------------------------------

class TestExitPlanMode:
    def setup_method(self):
        self.mod = _load_guardrail()

    def test_surfaces_plan_content_when_template_valid(self, tmp_path):
        plan_file = tmp_path / "my-plan.md"
        plan_file.write_text(VALID_PLAN_CONTENT)
        state = make_plan_state(phase="write", plan_file=str(plan_file))
        state_file = make_state_file(tmp_path, state)
        decision, _ = self.mod._dispatch(exit_plan_mode_input(), state_file)
        # Should return JSON with additionalContext
        assert decision.startswith("{")
        data = json.loads(decision)
        assert "additionalContext" in data

    def test_blocks_when_template_invalid(self, tmp_path):
        plan_file = tmp_path / "bad-plan.md"
        plan_file.write_text(INVALID_PLAN_CONTENT)
        state = make_plan_state(phase="write", plan_file=str(plan_file))
        state_file = make_state_file(tmp_path, state)
        decision, reason = self.mod._dispatch(exit_plan_mode_input(), state_file)
        assert decision == "block"
        assert "missing" in reason.lower() or "Context" in reason

    def test_handles_missing_plan_file_gracefully(self, tmp_path):
        state = make_plan_state(phase="write", plan_file=None)
        state_file = make_state_file(tmp_path, state)
        decision, reason = self.mod._dispatch(exit_plan_mode_input(), state_file)
        assert decision == "block"


# ---------------------------------------------------------------------------
# TestCLI
# ---------------------------------------------------------------------------

class TestCLI:
    def test_hook_input_arg_returns_allow(self, tmp_path):
        import subprocess
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({}))
        inp = skill_input("other", "")
        env_patch = {"PLAN_GUARDRAIL_STATE_PATH": str(state_file)}
        import os
        env = {**os.environ, **env_patch}
        result = subprocess.run(
            [sys.executable, str(PLAN_GUARDRAIL), "--hook-input", json.dumps(inp)],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0
        assert "allow" in result.stdout

    def test_hook_input_arg_returns_block(self, tmp_path):
        import subprocess, os
        # workflow active, write phase, write outside plans dir
        state = {"plan_workflow": make_plan_state(phase="write")}
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))
        inp = write_input("src/foo.py")
        env = {**os.environ, "PLAN_GUARDRAIL_STATE_PATH": str(state_file)}
        result = subprocess.run(
            [sys.executable, str(PLAN_GUARDRAIL), "--hook-input", json.dumps(inp)],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0
        assert result.stdout.strip().startswith("block")

    def test_reason_flag_includes_message(self, tmp_path):
        import subprocess, os
        state = {"plan_workflow": make_plan_state(phase="write")}
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state))
        inp = write_input("src/foo.py")
        env = {**os.environ, "PLAN_GUARDRAIL_STATE_PATH": str(state_file)}
        result = subprocess.run(
            [sys.executable, str(PLAN_GUARDRAIL), "--hook-input", json.dumps(inp), "--reason"],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0
        output = result.stdout.strip()
        assert output.startswith("block,") or output.startswith("block, ")
        assert len(output) > len("block")
