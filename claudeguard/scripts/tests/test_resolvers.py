import pytest
from models.state import Agent
from utils.resolvers import (
    resolve_explore,
    resolve_research,
    resolve_plan,
    resolve_plan_review,
    resolve_write_tests,
    resolve_test_review,
    resolve_write_code,
    resolve_code_review,
    resolve_quality_check,
    resolve_pr_create,
    resolve_ci_check,
    resolve_report,
    resolve,
)

try:
    from utils.resolvers import resolve_install_dependencies, resolve_define_contracts
except ImportError:
    resolve_install_dependencies = None
    resolve_define_contracts = None


class TestResolveExplore:
    def test_completes_when_agents_done(self, config, state):
        state.add_phase("explore")
        state.add_agent(Agent(name="Explore", status="completed"))
        resolve_explore(config, state)
        assert state.is_phase_completed("explore")

    def test_does_not_complete_when_agent_in_progress(self, config, state):
        state.add_phase("explore")
        state.add_agent(Agent(name="Explore", status="in_progress"))
        resolve_explore(config, state)
        assert not state.is_phase_completed("explore")

    def test_does_not_complete_when_no_agents(self, config, state):
        state.add_phase("explore")
        resolve_explore(config, state)
        assert not state.is_phase_completed("explore")


class TestResolveResearch:
    def test_completes_when_agents_done(self, config, state):
        state.add_phase("research")
        state.add_agent(Agent(name="Research", status="completed"))
        resolve_research(config, state)
        assert state.is_phase_completed("research")


class TestResolvePlan:
    def test_completes_when_agent_done_and_written(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        state.set_plan_file_path(".claude/plans/latest-plan.md")
        state.set_plan_written(True)
        resolve_plan(config, state)
        assert state.is_phase_completed("plan")

    def test_does_not_complete_when_not_written(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        resolve_plan(config, state)
        assert not state.is_phase_completed("plan")

    def test_does_not_complete_when_agent_not_done(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="in_progress", tool_use_id="p-1"))
        state.set_plan_file_path(".claude/plans/latest-plan.md")
        state.set_plan_written(True)
        resolve_plan(config, state)
        assert not state.is_phase_completed("plan")


class TestResolvePlanReview:
    def test_pass_completes_phase(self, config, state):
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 95, "quality_score": 95})
        resolve_plan_review(config, state)
        assert state.is_phase_completed("plan-review")
        assert state.last_plan_review["status"] == "Pass"

    def test_fail_requires_revision(self, config, state):
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 50, "quality_score": 50})
        resolve_plan_review(config, state)
        assert not state.is_phase_completed("plan-review")
        assert state.last_plan_review["status"] == "Fail"
        assert state.plan_revised is False

    def test_third_fail_does_not_raise(self, config, state):
        """3rd failed review sets status without raising — agent max prevents 4th."""
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_plan_review_status("Fail")
        state.add_plan_review({"confidence_score": 60, "quality_score": 60})
        state.set_last_plan_review_status("Fail")
        state.add_plan_review({"confidence_score": 70, "quality_score": 70})
        resolve_plan_review(config, state)
        assert state.last_plan_review["status"] == "Fail"
        assert not state.is_phase_completed("plan-review")


class TestResolveWriteTests:
    def test_completes_when_written_and_executed(self, state):
        state.add_phase("write-tests")
        state.add_test_file("test_app.py")
        state.set_tests_executed(True)
        resolve_write_tests(state)
        assert state.is_phase_completed("write-tests")

    def test_does_not_complete_without_execution(self, state):
        state.add_phase("write-tests")
        state.add_test_file("test_app.py")
        resolve_write_tests(state)
        assert not state.is_phase_completed("write-tests")


class TestResolveTestReview:
    def test_pass_completes_phase(self, config, state):
        state.add_phase("test-review")
        state.add_test_review("Pass")
        resolve_test_review(config, state)
        assert state.is_phase_completed("test-review")

    def test_fail_does_not_complete(self, config, state):
        state.add_phase("test-review")
        state.add_test_review("Fail")
        resolve_test_review(config, state)
        assert not state.is_phase_completed("test-review")

    def test_no_review_does_nothing(self, config, state):
        state.add_phase("test-review")
        resolve_test_review(config, state)
        assert not state.is_phase_completed("test-review")

    def test_third_fail_does_not_raise(self, config, state):
        """3rd failed review sets verdict without raising — agent max prevents 4th."""
        state.add_phase("test-review")
        state.add_test_review("Fail")
        state.add_test_review("Fail")
        state.add_test_review("Fail")
        resolve_test_review(config, state)
        assert state.last_test_review["verdict"] == "Fail"
        assert not state.is_phase_completed("test-review")


class TestResolveWriteCode:
    def test_completes_when_all_written(self, state):
        state.add_phase("write-code")
        state.add_code_file_to_write("app.py")
        state.add_code_file_to_write("utils.py")
        state.add_code_file("app.py")
        state.add_code_file("utils.py")
        resolve_write_code(state)
        assert state.is_phase_completed("write-code")

    def test_does_not_complete_when_missing(self, state):
        state.add_phase("write-code")
        state.add_code_file_to_write("app.py")
        state.add_code_file_to_write("utils.py")
        state.add_code_file("app.py")
        resolve_write_code(state)
        assert not state.is_phase_completed("write-code")


class TestResolveCodeReview:
    def test_pass_completes_phase(self, config, state):
        state.add_phase("code-review")
        state.add_code_review({"confidence_score": 95, "quality_score": 95})
        resolve_code_review(config, state)
        assert state.is_phase_completed("code-review")
        assert state.last_code_review["status"] == "Pass"

    def test_fail_requires_revision(self, config, state):
        state.add_phase("code-review")
        state.add_code_review({"confidence_score": 50, "quality_score": 50})
        resolve_code_review(config, state)
        assert not state.is_phase_completed("code-review")
        assert state.last_code_review["status"] == "Fail"
        assert state.files_to_revise == []
        assert state.files_revised == []

    def test_third_fail_does_not_raise(self, config, state):
        """3rd failed review sets status without raising — agent max prevents 4th."""
        state.add_phase("code-review")
        state.add_code_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_code_review_status("Fail")
        state.add_code_review({"confidence_score": 60, "quality_score": 60})
        state.set_last_code_review_status("Fail")
        state.add_code_review({"confidence_score": 70, "quality_score": 70})
        resolve_code_review(config, state)
        assert state.last_code_review["status"] == "Fail"
        assert not state.is_phase_completed("code-review")


class TestResolveQualityCheck:
    def test_pass_completes(self, state):
        state.add_phase("quality-check")
        state.set_quality_check_result("Pass")
        resolve_quality_check(state)
        assert state.is_phase_completed("quality-check")

    def test_fail_does_not_complete(self, state):
        state.add_phase("quality-check")
        state.set_quality_check_result("Fail")
        resolve_quality_check(state)
        assert not state.is_phase_completed("quality-check")


class TestResolvePrCreate:
    def test_completes_when_created(self, state):
        state.add_phase("pr-create")
        state.set_pr_status("created")
        resolve_pr_create(state)
        assert state.is_phase_completed("pr-create")


class TestResolveCiCheck:
    def test_completes_when_passed(self, state):
        state.add_phase("ci-check")
        state.set_ci_status("passed")
        resolve_ci_check(state)
        assert state.is_phase_completed("ci-check")


class TestResolveReport:
    def test_completes_when_written(self, state):
        state.add_phase("write-report")
        state.set_report_written(True)
        resolve_report(state)
        assert state.is_phase_completed("write-report")


class TestResolveDispatcher:
    def test_dispatches_to_correct_resolver(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        state.set_plan_file_path(".claude/plans/latest-plan.md")
        state.set_plan_written(True)
        resolve(config, state)
        assert state.is_phase_completed("plan")

    def test_unknown_phase_does_nothing(self, config, state):
        state.add_phase("unknown-phase")
        resolve(config, state)
        assert state.get_phase_status("unknown-phase") == "in_progress"

    def test_dispatches_install_deps(self, config, state):
        state.add_phase("install-deps")
        state.set_dependencies_installed()
        resolve(config, state)
        assert state.is_phase_completed("install-deps")

    def test_dispatches_define_contracts(self, config, state):
        state.add_phase("define-contracts")
        state.set_contracts_written(True)
        state.set_contracts_validated(True)
        resolve(config, state)
        assert state.is_phase_completed("define-contracts")


# ═══════════════════════════════════════════════════════════════════
# resolve_install_dependencies
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.skipif(resolve_install_dependencies is None, reason="Not yet implemented")
class TestResolveInstallDependencies:
    def test_completes_when_installed(self, state):
        state.add_phase("install-deps")
        state.set_dependencies_installed()
        resolve_install_dependencies(state)
        assert state.is_phase_completed("install-deps")

    def test_does_not_complete_when_not_installed(self, state):
        state.add_phase("install-deps")
        resolve_install_dependencies(state)
        assert not state.is_phase_completed("install-deps")

    def test_does_not_complete_with_packages_but_not_installed(self, state):
        state.add_phase("install-deps")
        state.set_dependencies_packages(["flask", "pytest"])
        resolve_install_dependencies(state)
        assert not state.is_phase_completed("install-deps")


# ═══════════════════════════════════════════════════════════════════
# resolve_define_contracts
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.skipif(resolve_define_contracts is None, reason="Not yet implemented")
class TestResolveDefineContracts:
    def test_completes_when_written_and_validated(self, state):
        state.add_phase("define-contracts")
        state.set_contracts_written(True)
        state.set_contracts_validated(True)
        resolve_define_contracts(state)
        assert state.is_phase_completed("define-contracts")

    def test_does_not_complete_when_not_written(self, state):
        state.add_phase("define-contracts")
        state.set_contracts_validated(True)
        resolve_define_contracts(state)
        assert not state.is_phase_completed("define-contracts")

    def test_does_not_complete_when_not_validated(self, state):
        state.add_phase("define-contracts")
        state.set_contracts_written(True)
        resolve_define_contracts(state)
        assert not state.is_phase_completed("define-contracts")

    def test_does_not_complete_when_neither(self, state):
        state.add_phase("define-contracts")
        resolve_define_contracts(state)
        assert not state.is_phase_completed("define-contracts")
