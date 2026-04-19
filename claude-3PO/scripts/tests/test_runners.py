import pytest
from models.state import Agent
from handlers.guardrails.stop_guard import StopGuard


class TestCheckPhases:
    def test_all_completed(self, config, state):
        workflow_type = state.get("workflow_type", "build")
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
        workflow_type = state.get("workflow_type", "build")
        phases = config.get_phases(workflow_type) or config.main_phases
        state.set("skip", phases)
        guard = StopGuard(config, state)
        guard.check_phases()  # all skipped, should pass

    def test_inset_phase_completed(self, config, state):
        workflow_type = state.get("workflow_type", "build")
        phases = config.get_phases(workflow_type) or config.main_phases
        for phase in phases:
            state.add_phase(phase)
        # none completed
        guard = StopGuard(config, state)
        with pytest.raises(ValueError, match="not completed"):
            guard.check_phases()


class TestCheckTests:
    def test_all_passing(self, config, state):
        state.add_test_file("test_app.py")
        state.set_tests_executed(True)
        state.add_test_review("Pass")
        guard = StopGuard(config, state)
        guard.check_tests()  # should not raise

    def test_no_test_files(self, config, state):
        guard = StopGuard(config, state)
        with pytest.raises(ValueError, match="No test files"):
            guard.check_tests()

    def test_not_executed(self, config, state):
        state.add_test_file("test_app.py")
        guard = StopGuard(config, state)
        with pytest.raises(ValueError, match="not executed"):
            guard.check_tests()

    def test_review_failed(self, config, state):
        state.add_test_file("test_app.py")
        state.set_tests_executed(True)
        state.add_test_review("Fail")
        guard = StopGuard(config, state)
        with pytest.raises(ValueError, match="verdict"):
            guard.check_tests()

    def test_skipped(self, config, state):
        state.set("skip", ["write-tests", "test-review"])
        guard = StopGuard(config, state)
        guard.check_tests()  # should not raise


class TestCheckCI:
    def test_passed(self, config, state):
        state.set_ci_status("passed")
        guard = StopGuard(config, state)
        guard.check_ci()  # should not raise

    def test_failed(self, config, state):
        state.set_ci_status("failed")
        guard = StopGuard(config, state)
        with pytest.raises(ValueError, match="CI checks failed"):
            guard.check_ci()

    def test_pending(self, config, state):
        guard = StopGuard(config, state)
        with pytest.raises(ValueError, match="CI status"):
            guard.check_ci()

    def test_skipped(self, config, state):
        state.set("skip", ["ci-check"])
        guard = StopGuard(config, state)
        guard.check_ci()  # should not raise
