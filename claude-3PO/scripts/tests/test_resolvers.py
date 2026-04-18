import pytest
from models.state import Agent
from utils.resolver import Resolver, resolve


class TestResolveExplore:
    def test_completes_when_agents_done(self, config, state):
        state.add_phase("explore")
        state.add_agent(Agent(name="Explore", status="completed"))
        Resolver(config, state)._resolve_explore()
        assert state.is_phase_completed("explore")

    def test_does_not_complete_when_agent_in_progress(self, config, state):
        state.add_phase("explore")
        state.add_agent(Agent(name="Explore", status="in_progress"))
        Resolver(config, state)._resolve_explore()
        assert not state.is_phase_completed("explore")

    def test_does_not_complete_when_no_agents(self, config, state):
        state.add_phase("explore")
        Resolver(config, state)._resolve_explore()
        assert not state.is_phase_completed("explore")


class TestResolveResearch:
    def test_completes_when_agents_done(self, config, state):
        state.add_phase("research")
        state.add_agent(Agent(name="Research", status="completed"))
        Resolver(config, state)._resolve_research()
        assert state.is_phase_completed("research")


class TestResolvePlan:
    def test_completes_when_agent_done_and_written(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        state.set_plan_file_path(".claude/plans/latest-plan.md")
        state.set_plan_written(True)
        Resolver(config, state)._resolve_plan()
        assert state.is_phase_completed("plan")

    def test_does_not_complete_when_not_written(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        Resolver(config, state)._resolve_plan()
        assert not state.is_phase_completed("plan")

    def test_does_not_complete_when_agent_not_done(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="in_progress", tool_use_id="p-1"))
        state.set_plan_file_path(".claude/plans/latest-plan.md")
        state.set_plan_written(True)
        Resolver(config, state)._resolve_plan()
        assert not state.is_phase_completed("plan")


class TestResolvePlanReview:
    def test_pass_completes_phase(self, config, state):
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 95, "quality_score": 95})
        Resolver(config, state)._resolve_plan_review()
        assert state.is_phase_completed("plan-review")
        assert state.last_plan_review["status"] == "Pass"

    def test_fail_requires_revision(self, config, state):
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 50, "quality_score": 50})
        Resolver(config, state)._resolve_plan_review()
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
        Resolver(config, state)._resolve_plan_review()
        assert state.last_plan_review["status"] == "Fail"
        assert not state.is_phase_completed("plan-review")


class TestResolveWriteTests:
    def test_completes_when_written_and_executed(self, config, state):
        state.add_phase("write-tests")
        state.add_test_file("test_app.py")
        state.set_tests_executed(True)
        Resolver(config, state)._resolve_write_tests()
        assert state.is_phase_completed("write-tests")

    def test_does_not_complete_without_execution(self, config, state):
        state.add_phase("write-tests")
        state.add_test_file("test_app.py")
        Resolver(config, state)._resolve_write_tests()
        assert not state.is_phase_completed("write-tests")


class TestResolveTestReview:
    def test_pass_completes_phase(self, config, state):
        state.add_phase("test-review")
        state.add_test_review("Pass")
        Resolver(config, state)._resolve_test_review()
        assert state.is_phase_completed("test-review")

    def test_fail_does_not_complete(self, config, state):
        state.add_phase("test-review")
        state.add_test_review("Fail")
        Resolver(config, state)._resolve_test_review()
        assert not state.is_phase_completed("test-review")

    def test_no_review_does_nothing(self, config, state):
        state.add_phase("test-review")
        Resolver(config, state)._resolve_test_review()
        assert not state.is_phase_completed("test-review")

    def test_third_fail_does_not_raise(self, config, state):
        """3rd failed review sets verdict without raising — agent max prevents 4th."""
        state.add_phase("test-review")
        state.add_test_review("Fail")
        state.add_test_review("Fail")
        state.add_test_review("Fail")
        Resolver(config, state)._resolve_test_review()
        assert state.last_test_review["verdict"] == "Fail"
        assert not state.is_phase_completed("test-review")


class TestResolveWriteCode:
    def test_completes_when_all_written(self, config, state):
        state.add_phase("write-code")
        state.add_code_file_to_write("app.py")
        state.add_code_file_to_write("utils.py")
        state.add_code_file("app.py")
        state.add_code_file("utils.py")
        Resolver(config, state)._resolve_write_code()
        assert state.is_phase_completed("write-code")

    def test_does_not_complete_when_missing(self, config, state):
        state.add_phase("write-code")
        state.add_code_file_to_write("app.py")
        state.add_code_file_to_write("utils.py")
        state.add_code_file("app.py")
        Resolver(config, state)._resolve_write_code()
        assert not state.is_phase_completed("write-code")


class TestResolveCodeReview:
    def test_pass_completes_phase(self, config, state):
        state.add_phase("code-review")
        state.add_code_review({"confidence_score": 95, "quality_score": 95})
        Resolver(config, state)._resolve_code_review()
        assert state.is_phase_completed("code-review")
        assert state.last_code_review["status"] == "Pass"

    def test_fail_requires_revision(self, config, state):
        state.add_phase("code-review")
        state.add_code_review({"confidence_score": 50, "quality_score": 50})
        Resolver(config, state)._resolve_code_review()
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
        Resolver(config, state)._resolve_code_review()
        assert state.last_code_review["status"] == "Fail"
        assert not state.is_phase_completed("code-review")


class TestResolveQualityCheck:
    def test_pass_completes(self, config, state):
        state.add_phase("quality-check")
        state.set_quality_check_result("Pass")
        Resolver(config, state)._resolve_quality_check()
        assert state.is_phase_completed("quality-check")

    def test_fail_does_not_complete(self, config, state):
        state.add_phase("quality-check")
        state.set_quality_check_result("Fail")
        Resolver(config, state)._resolve_quality_check()
        assert not state.is_phase_completed("quality-check")


class TestResolvePrCreate:
    def test_completes_when_created(self, config, state):
        state.add_phase("pr-create")
        state.set_pr_status("created")
        Resolver(config, state)._resolve_pr_create()
        assert state.is_phase_completed("pr-create")


class TestResolveCiCheck:
    def test_completes_when_passed(self, config, state):
        state.add_phase("ci-check")
        state.set_ci_status("passed")
        Resolver(config, state)._resolve_ci_check()
        assert state.is_phase_completed("ci-check")


class TestResolveReport:
    def test_completes_when_written(self, config, state):
        state.add_phase("write-report")
        state.set_report_written(True)
        Resolver(config, state)._resolve_report()
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
