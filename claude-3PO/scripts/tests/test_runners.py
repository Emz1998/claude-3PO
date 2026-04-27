import pytest
from models.state import Agent
from handlers.guardrails.stop_guard import StopGuard


class TestCheckPhases:
    def test_all_completed(self, config, state):
        workflow_type = state.get("workflow_type", "implement")
        phases = config.get_phases(workflow_type) or config.main_phases
        for phase in phases:
            state.add_phase(phase)
            state.set_phase_completed(phase)
        guard = StopGuard(config, state)
        guard.check_phases()  # should not raise

    def test_missing_phase(self, config, state):
        state.add_phase("explore")
        state.set_phase_completed("explore")
        guard = StopGuard(config, state)
        with pytest.raises(ValueError, match="not completed"):
            guard.check_phases()

    def test_skipped_phases_ignored(self, config, state):
        workflow_type = state.get("workflow_type", "implement")
        phases = config.get_phases(workflow_type) or config.main_phases
        state.set("skip", phases)
        guard = StopGuard(config, state)
        guard.check_phases()  # all skipped, should pass

    def test_inset_phase_completed(self, config, state):
        workflow_type = state.get("workflow_type", "implement")
        phases = config.get_phases(workflow_type) or config.main_phases
        for phase in phases:
            state.add_phase(phase)
        # none completed
        guard = StopGuard(config, state)
        with pytest.raises(ValueError, match="not completed"):
            guard.check_phases()
