import pytest
from models.state import Agent
from helpers import make_hook_input


class TestPhases:
    def test_add_phase(self, state):
        state.add_phase("explore")
        assert state.current_phase == "explore"
        assert state.get_phase_status("explore") == "in_progress"

    def test_complete_phase(self, state):
        state.add_phase("explore")
        state.complete_phase("explore")
        assert state.is_phase_completed("explore")
        assert state.get_phase_status("explore") == "completed"

    def test_current_phase_is_last(self, state):
        state.add_phase("explore")
        state.add_phase("research")
        assert state.current_phase == "research"

    def test_empty_phases(self, state):
        assert state.current_phase == ""
        assert state.get_phase_status("explore") is None


class TestSubPhases:
    def test_add_sub_phase(self, state):
        state.add_sub_phase("plan-revision")
        assert state.sub_phase == "plan-revision"

    def test_complete_sub_phase(self, state):
        state.add_sub_phase("refactor")
        state.complete_sub_phase("refactor")
        subs = state.sub_phases
        assert subs[0]["status"] == "completed"


class TestAgents:
    def test_add_agent(self, state):
        state.add_agent(Agent(name="Explore", status="in_progress"))
        assert state.count_agents("Explore") == 1

    def test_get_agent(self, state):
        state.add_agent(Agent(name="Explore", status="in_progress"))
        agent = state.get_agent("Explore")
        assert agent["name"] == "Explore"
        assert agent["status"] == "in_progress"

    def test_update_agent_status_by_id(self, state):
        state.add_agent(Agent(name="Explore", status="in_progress", tool_use_id="agent-001"))
        state.update_agent_status("agent-001", "completed")
        agent = state.get_agent("Explore")
        assert agent["status"] == "completed"

    def test_count_multiple_agents(self, state):
        state.add_agent(Agent(name="Explore", status="in_progress"))
        state.add_agent(Agent(name="Explore", status="in_progress"))
        assert state.count_agents("Explore") == 2


class TestPlan:
    def test_set_plan_file_path(self, state):
        state.set_plan_file_path(".claude/plans/plan.md")
        assert state.plan["file_path"] == ".claude/plans/plan.md"

    def test_set_plan_written(self, state):
        state.set_plan_written(True)
        assert state.plan["written"] is True

    def test_plan_review_scores(self, state):
        scores = {"confidence_score": 85, "quality_score": 90}
        state.set_plan_review_scores(scores)
        assert state.plan["review"]["scores"] == scores

    def test_plan_review_status(self, state):
        state.set_plan_review_status("Pass")
        assert state.plan["review"]["status"] == "Pass"

    def test_increment_plan_review_iteration(self, state):
        state.increment_plan_review_iteration()
        assert state.plan["review"]["iteration"] == 1
        state.increment_plan_review_iteration()
        assert state.plan["review"]["iteration"] == 2


class TestTests:
    def test_add_test_file(self, state):
        state.add_test_file("test_app.py")
        assert "test_app.py" in state.tests["file_paths"]

    def test_add_test_file_dedup(self, state):
        state.add_test_file("test_app.py")
        state.add_test_file("test_app.py")
        assert state.tests["file_paths"].count("test_app.py") == 1

    def test_set_tests_review_result(self, state):
        state.set_tests_review_result("Pass")
        assert state.tests["review_result"] == "Pass"

    def test_set_tests_executed(self, state):
        state.set_tests_executed(True)
        assert state.tests["executed"] is True


class TestCodeFiles:
    def test_add_code_file(self, state):
        state.add_code_file("app.py")
        assert "app.py" in state.code_files["file_paths"]

    def test_add_code_file_dedup(self, state):
        state.add_code_file("app.py")
        state.add_code_file("app.py")
        assert state.code_files["file_paths"].count("app.py") == 1

    def test_code_files_to_write(self, state):
        state.add_code_file_to_write("app.py")
        assert "app.py" in state.code_files_to_write

    def test_code_review_scores(self, state):
        scores = {"confidence_score": 95, "quality_score": 92}
        state.set_code_review_scores(scores)
        assert state.code_files["review"]["scores"] == scores

    def test_code_review_status(self, state):
        state.set_code_review_status("Pass")
        assert state.code_files["review"]["status"] == "Pass"

    def test_increment_code_review_iteration(self, state):
        state.increment_code_review_iteration()
        assert state.code_files["review"]["iteration"] == 1


class TestPR:
    def test_pr_status(self, state):
        assert state.pr_status == "pending"
        state.set_pr_status("created")
        assert state.pr_status == "created"

    def test_pr_number(self, state):
        assert state.pr_number is None
        state.set_pr_number(42)
        assert state.pr_number == 42


class TestCI:
    def test_ci_status(self, state):
        assert state.ci_status == "pending"
        state.set_ci_status("passed")
        assert state.ci_status == "passed"

    def test_ci_results(self, state):
        results = [{"name": "build", "conclusion": "SUCCESS"}]
        state.set_ci_results(results)
        assert state.ci_results == results


class TestReport:
    def test_report_written(self, state):
        assert state.report_written is False
        state.set_report_written(True)
        assert state.report_written is True


class TestQualityCheck:
    def test_quality_check_result(self, state):
        assert state.quality_check_result is None
        state.set_quality_check_result("Pass")
        assert state.quality_check_result == "Pass"
