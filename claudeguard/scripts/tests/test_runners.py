import pytest
from models.state import Agent
from utils.runners import check_phases, check_tests, check_ci


class TestCheckPhases:
    def test_all_completed(self, config, state):
        for phase in config.main_phases:
            state.add_phase(phase)
            state.complete_phase(phase)
        check_phases(config, state)  # should not exit

    def test_missing_phase(self, config, state):
        state.add_phase("explore")
        state.complete_phase("explore")
        with pytest.raises(SystemExit) as exc:
            check_phases(config, state)
        assert exc.value.code == 1

    def test_skipped_phases_ignored(self, config, state):
        state.set("skip", config.main_phases)
        check_phases(config, state)  # all skipped, should pass

    def test_incomplete_phase(self, config, state):
        for phase in config.main_phases:
            state.add_phase(phase)
        # none completed
        with pytest.raises(SystemExit) as exc:
            check_phases(config, state)
        assert exc.value.code == 1


class TestCheckTests:
    def test_all_passing(self, state):
        state.add_test_file("test_app.py")
        state.set_tests_executed(True)
        state.add_test_review("Pass")
        check_tests(state)  # should not exit

    def test_no_test_files(self, state):
        with pytest.raises(SystemExit) as exc:
            check_tests(state)
        assert exc.value.code == 1

    def test_not_executed(self, state):
        state.add_test_file("test_app.py")
        with pytest.raises(SystemExit) as exc:
            check_tests(state)
        assert exc.value.code == 1

    def test_review_failed(self, state):
        state.add_test_file("test_app.py")
        state.set_tests_executed(True)
        state.add_test_review("Fail")
        with pytest.raises(SystemExit) as exc:
            check_tests(state)
        assert exc.value.code == 1

    def test_skipped(self, state):
        state.set("skip", ["write-tests", "test-review"])
        check_tests(state)  # should not exit


class TestCheckCI:
    def test_passed(self, state):
        state.set_ci_status("passed")
        check_ci(state)  # should not exit

    def test_failed(self, state):
        state.set_ci_status("failed")
        with pytest.raises(SystemExit) as exc:
            check_ci(state)
        assert exc.value.code == 1

    def test_pending(self, state):
        with pytest.raises(SystemExit) as exc:
            check_ci(state)
        assert exc.value.code == 1

    def test_skipped(self, state):
        state.set("skip", ["ci-check"])
        check_ci(state)  # should not exit
