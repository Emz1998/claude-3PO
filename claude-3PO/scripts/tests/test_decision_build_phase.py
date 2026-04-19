"""Tests for the /decision phase being shared between specs and build.

The same resolver, command, and state setters serve both workflows. In
build, /decision sits between /research and /plan; the agent writes to
``projects/docs/decisions.md`` and the phase completes when that doc is
flagged written.
"""

import pytest

from utils.resolver import Resolver, resolve
from helpers import make_hook_input, invoke_phase_guard as phase_guard


class TestDecisionPhaseInBuildWorkflow:
    def test_decision_in_build_phase_list(self, config):
        assert "decision" in config.get_phases("build")

    def test_decision_completes_when_decisions_doc_written(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("decision")
        state.specs.set_doc_written("decisions", True)
        Resolver(config, state)._resolve_doc_phase("decision", "decisions")
        assert state.is_phase_completed("decision")

    def test_decision_does_not_complete_without_doc(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("decision")
        Resolver(config, state)._resolve_doc_phase("decision", "decisions")
        assert not state.is_phase_completed("decision")


class TestDecisionTransitions:
    """Phase guard accepts /decision after /research in build."""

    def test_decision_after_research_completed(self, config, state):
        state.set("workflow_type", "build")
        # clarify is auto-skipped
        def _seed(d):
            d.setdefault("phases", []).append({"name": "clarify", "status": "skipped"})
        state.update(_seed)
        state.add_phase("explore")
        state.set_phase_completed("explore")
        state.add_phase("research")
        state.set_phase_completed("research")

        hook = make_hook_input("Skill", {"skill": "decision"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "allow"

    def test_decision_blocked_before_research(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("explore")
        state.set_phase_completed("explore")

        hook = make_hook_input("Skill", {"skill": "decision"})
        decision, msg = phase_guard(hook, config, state)
        assert decision == "block"

    def test_plan_after_decision_completed(self, config, state):
        state.set("workflow_type", "build")
        def _seed(d):
            d.setdefault("phases", []).append({"name": "clarify", "status": "skipped"})
        state.update(_seed)
        state.add_phase("explore")
        state.set_phase_completed("explore")
        state.add_phase("research")
        state.set_phase_completed("research")
        state.add_phase("decision")
        state.set_phase_completed("decision")

        hook = make_hook_input("Skill", {"skill": "plan"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "allow"
