"""Tests for /continue skill — force-completes the current phase and proceeds.

In the trimmed 7-phase MVP, /continue is the universal advancer; the plan
checkpoint pause is broken by /continue from the `plan` phase.
"""

import pytest
from lib.state_store import StateStore
from helpers import make_hook_input, invoke_phase_guard as phase_guard


class TestContinueForceCompletes:
    """/continue force-completes any in-progress phase."""

    def test_continue_force_completes_non_review_phase(self, config, state):
        state.set("workflow_type", "implement")
        state.add_phase("write-code")

        hook = make_hook_input("Skill", {"skill": "continue"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "allow"
        assert state.is_phase_completed("write-code")


class TestContinueAfterCompleted:
    """Phase already completed — /continue auto-starts next."""

    def test_continue_after_plan_completed(self, config, state):
        state.set("workflow_type", "implement")
        state.add_phase("plan")
        state.set_phase_completed("plan")

        hook = make_hook_input("Skill", {"skill": "continue"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "allow"


class TestContinueBlocked:
    """/continue blocked when no phases exist."""

    def test_blocked_when_no_phases(self, config, state):
        hook = make_hook_input("Skill", {"skill": "continue"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "block"
