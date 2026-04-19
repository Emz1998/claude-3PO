"""Bug #1: violations logged before any phase is entered should label the first workflow phase."""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from utils.hooks.pre_tool_use import resolve_violation_phase  # noqa: E402
from helpers import make_hook_input  # noqa: E402


class TestResolveViolationPhase:
    def test_empty_phase_falls_back_to_pre_workflow_sentinel(self, config, state):
        """Before any phase is entered, fall back to an honest sentinel —
        not the first workflow phase, which would misleadingly label pre-vision
        writes as `vision`."""
        state.set("workflow_type", "specs")
        hook = make_hook_input("Write", {"file_path": "a.md"})
        assert resolve_violation_phase(state, config, "Write", hook) == "pre-workflow"

    def test_empty_phase_build_workflow_also_pre_workflow(self, config, state):
        state.set("workflow_type", "build")
        hook = make_hook_input("Agent", {"subagent_type": "Research"})
        assert resolve_violation_phase(state, config, "Agent", hook) == "pre-workflow"

    def test_current_phase_used_when_set(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("strategy")
        hook = make_hook_input("Write", {"file_path": "a.md"})
        assert resolve_violation_phase(state, config, "Write", hook) == "strategy"

    def test_current_phase_wins_over_attempted_skill(self, config, state):
        """Bug: /decision blocked from strategy was logged as phase=decision.
        Log consumers want the phase the user *was in*, not the skill they tried to jump to."""
        state.set("workflow_type", "build")
        state.add_phase("research")
        hook = make_hook_input("Skill", {"skill": "plan"})
        assert resolve_violation_phase(state, config, "Skill", hook) == "research"

    def test_skill_name_fallback_when_no_phase_active(self, config, state):
        state.set("workflow_type", "build")
        hook = make_hook_input("Skill", {"skill": "plan"})
        assert resolve_violation_phase(state, config, "Skill", hook) == "plan"
