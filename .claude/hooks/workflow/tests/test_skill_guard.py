"""Tests for guards/skill_guard.py."""

import json
import sys
from pathlib import Path

import pytest

WORKFLOW_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOW_DIR.parent))

from workflow.guards import skill_guard
from workflow.state_store import StateStore


def make_skill_post(skill: str, args: str = "", tmp_path=None) -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Skill",
        "tool_input": {"skill": skill, "args": args},
        "tool_response": {"success": True},
        "tool_use_id": "t1",
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


def make_user_prompt(prompt: str) -> dict:
    return {
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
        "session_id": "s", "transcript_path": "t", "cwd": ".", "permission_mode": "default",
    }


# ---------------------------------------------------------------------------
# Skill activation via PostToolUse
# ---------------------------------------------------------------------------

class TestSkillActivation:
    def test_plan_skill_activates_workflow(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        decision, reason = skill_guard.handle(make_skill_post("plan"), store)
        assert decision == "allow"
        state = store.load()
        assert state["workflow_active"] is True
        assert state["workflow_type"] == "plan"
        assert state["phase"] == "explore"

    def test_implement_skill_activates_workflow(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        decision, reason = skill_guard.handle(make_skill_post("implement"), store)
        assert decision == "allow"
        state = store.load()
        assert state["workflow_active"] is True
        assert state["workflow_type"] == "implement"
        assert state["phase"] == "explore"

    def test_non_matching_skill_is_allowed(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        decision, reason = skill_guard.handle(make_skill_post("brainstorm"), store)
        assert decision == "allow"
        state = store.load()
        assert not state.get("workflow_active")

    def test_plan_skip_all_sets_plan_phase(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        skill_guard.handle(make_skill_post("plan", "--skip-all"), store)
        state = store.load()
        assert state["phase"] == "plan"
        assert state["skip_explore"] is True
        assert state["skip_research"] is True

    def test_plan_skip_explore_only(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        skill_guard.handle(make_skill_post("plan", "--skip-explore"), store)
        state = store.load()
        assert state["skip_explore"] is True
        assert state["skip_research"] is False

    def test_plan_skip_research_only(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        skill_guard.handle(make_skill_post("plan", "--skip-research"), store)
        state = store.load()
        assert state["skip_explore"] is False
        assert state["skip_research"] is True

    def test_implement_skip_all_sets_plan_phase(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        skill_guard.handle(make_skill_post("implement", "--skip-all"), store)
        state = store.load()
        assert state["phase"] == "plan"

    def test_implement_tdd_flag(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        skill_guard.handle(make_skill_post("implement", "--tdd"), store)
        state = store.load()
        assert state["tdd"] is True

    def test_implement_no_tdd_flag(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        skill_guard.handle(make_skill_post("implement"), store)
        state = store.load()
        assert state["tdd"] is False

    def test_instructions_extracted(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        skill_guard.handle(make_skill_post("plan", "--skip-all implement login flow"), store)
        state = store.load()
        assert "implement login flow" in state["instructions"]

    def test_plan_initializes_full_state_fields(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        skill_guard.handle(make_skill_post("plan"), store)
        state = store.load()
        assert "agents" in state
        assert state["plan_file"] is None
        assert state["plan_written"] is False
        assert state["plan_review_iteration"] == 0


# ---------------------------------------------------------------------------
# Skill activation via UserPromptSubmit
# ---------------------------------------------------------------------------

class TestUserPromptSubmit:
    def test_plan_prompt_activates_workflow(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        decision, _ = skill_guard.handle(make_user_prompt("/plan"), store)
        assert decision == "allow"
        state = store.load()
        assert state["workflow_active"] is True
        assert state["workflow_type"] == "plan"

    def test_implement_prompt_activates_workflow(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        decision, _ = skill_guard.handle(make_user_prompt("/implement --tdd"), store)
        assert decision == "allow"
        state = store.load()
        assert state["workflow_type"] == "implement"
        assert state["tdd"] is True

    def test_non_skill_prompt_ignored(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        decision, _ = skill_guard.handle(make_user_prompt("Hello world"), store)
        assert decision == "allow"
        assert not store.load().get("workflow_active")

    def test_plan_prompt_with_args(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        skill_guard.handle(make_user_prompt("/plan --skip-all fix the bug"), store)
        state = store.load()
        assert state["skip_explore"] is True
        assert "fix the bug" in state["instructions"]

    def test_story_id_extracted_from_implement(self, tmp_state_file):
        store = StateStore(tmp_state_file)
        skill_guard.handle(make_user_prompt("/implement SK-123 --tdd"), store)
        state = store.load()
        assert state["story_id"] == "SK-123"
