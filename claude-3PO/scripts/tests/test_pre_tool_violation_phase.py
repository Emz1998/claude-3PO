"""Bug #1: violations logged before any phase is entered should label the first workflow phase."""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
DISPATCHERS = SCRIPTS_DIR / "dispatchers"
if str(DISPATCHERS) not in sys.path:
    sys.path.insert(0, str(DISPATCHERS))

from pre_tool_use import resolve_violation_phase  # noqa: E402
from helpers import make_hook_input  # noqa: E402


class TestResolveViolationPhase:
    def test_empty_phase_falls_back_to_first_workflow_phase(self, config, state):
        state.set("workflow_type", "specs")
        hook = make_hook_input("Write", {"file_path": "a.md"})
        assert resolve_violation_phase(state, config, "Write", hook) == "vision"

    def test_empty_phase_falls_back_to_build_first_phase(self, config, state):
        state.set("workflow_type", "build")
        hook = make_hook_input("Agent", {"subagent_type": "Research"})
        assert resolve_violation_phase(state, config, "Agent", hook) == "explore"

    def test_current_phase_used_when_set(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("strategy")
        hook = make_hook_input("Write", {"file_path": "a.md"})
        assert resolve_violation_phase(state, config, "Write", hook) == "strategy"

    def test_skill_name_wins_for_skill_tool(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("research")
        hook = make_hook_input("Skill", {"skill": "install-deps"})
        assert resolve_violation_phase(state, config, "Skill", hook) == "install-deps"
