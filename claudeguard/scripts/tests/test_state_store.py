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


class TestPlanRevision:
    def test_plan_revised_default(self, state):
        assert state.plan_revised is False

    def test_set_plan_revised(self, state):
        state.set_plan_revised(True)
        assert state.plan_revised is True

    def test_reset_plan_revised(self, state):
        state.set_plan_revised(True)
        state.set_plan_revised(False)
        assert state.plan_revised is False


class TestCodeRevision:
    def test_files_to_revise_default(self, state):
        assert state.files_to_revise == []

    def test_set_files_to_revise(self, state):
        state.set_files_to_revise(["src/app.py", "src/utils.py"])
        assert state.files_to_revise == ["src/app.py", "src/utils.py"]

    def test_files_revised_default(self, state):
        assert state.files_revised == []

    def test_add_file_revised(self, state):
        state.add_file_revised("src/app.py")
        assert "src/app.py" in state.files_revised

    def test_all_files_revised(self, state):
        state.set_files_to_revise(["src/app.py", "src/utils.py"])
        state.add_file_revised("src/app.py")
        assert not state.all_files_revised
        state.add_file_revised("src/utils.py")
        assert state.all_files_revised

    def test_reset_revision_tracking(self, state):
        state.set_files_to_revise(["src/app.py"])
        state.add_file_revised("src/app.py")
        state.set_files_to_revise(["src/new.py"])
        assert state.files_revised == []
        assert state.files_to_revise == ["src/new.py"]

    def test_code_tests_to_revise_default(self, state):
        assert state.code_tests_to_revise == []

    def test_set_code_tests_to_revise(self, state):
        state.set_code_tests_to_revise(["test_app.py"])
        assert state.code_tests_to_revise == ["test_app.py"]

    def test_code_tests_revised_default(self, state):
        assert state.code_tests_revised == []

    def test_add_code_test_revised(self, state):
        state.add_code_test_revised("test_app.py")
        assert "test_app.py" in state.code_tests_revised

    def test_all_code_tests_revised(self, state):
        state.set_code_tests_to_revise(["test_app.py", "test_utils.py"])
        state.add_code_test_revised("test_app.py")
        assert not state.all_code_tests_revised
        state.add_code_test_revised("test_utils.py")
        assert state.all_code_tests_revised


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

    def test_add_plan_review(self, state):
        scores = {"confidence_score": 85, "quality_score": 90}
        state.add_plan_review(scores)
        assert state.plan_review_count == 1
        assert state.last_plan_review["scores"] == scores
        assert state.last_plan_review["status"] is None

    def test_set_last_plan_review_status(self, state):
        state.add_plan_review({"confidence_score": 85, "quality_score": 90})
        state.set_last_plan_review_status("Pass")
        assert state.last_plan_review["status"] == "Pass"

    def test_plan_review_count(self, state):
        state.add_plan_review({"confidence_score": 50, "quality_score": 50})
        state.add_plan_review({"confidence_score": 85, "quality_score": 90})
        assert state.plan_review_count == 2


class TestTests:
    def test_add_test_file(self, state):
        state.add_test_file("test_app.py")
        assert "test_app.py" in state.tests["file_paths"]

    def test_add_test_file_dedup(self, state):
        state.add_test_file("test_app.py")
        state.add_test_file("test_app.py")
        assert state.tests["file_paths"].count("test_app.py") == 1

    def test_set_tests_executed(self, state):
        state.set_tests_executed(True)
        assert state.tests["executed"] is True

    def test_add_test_review(self, state):
        state.add_test_review("Fail")
        assert state.test_review_count == 1
        assert state.last_test_review["verdict"] == "Fail"

    def test_test_review_count(self, state):
        state.add_test_review("Fail")
        state.add_test_review("Pass")
        assert state.test_review_count == 2

    def test_last_test_review(self, state):
        state.add_test_review("Fail")
        state.add_test_review("Pass")
        assert state.last_test_review["verdict"] == "Pass"


class TestTestRevision:
    def test_test_files_to_revise_default(self, state):
        assert state.test_files_to_revise == []

    def test_set_test_files_to_revise(self, state):
        state.set_test_files_to_revise(["test_app.py"])
        assert state.test_files_to_revise == ["test_app.py"]

    def test_test_files_revised_default(self, state):
        assert state.test_files_revised == []

    def test_add_test_file_revised(self, state):
        state.add_test_file_revised("test_app.py")
        assert "test_app.py" in state.test_files_revised

    def test_all_test_files_revised(self, state):
        state.set_test_files_to_revise(["test_app.py", "test_utils.py"])
        state.add_test_file_revised("test_app.py")
        assert not state.all_test_files_revised
        state.add_test_file_revised("test_utils.py")
        assert state.all_test_files_revised

    def test_reset_test_revision_tracking(self, state):
        state.set_test_files_to_revise(["test_app.py"])
        state.add_test_file_revised("test_app.py")
        state.set_test_files_to_revise(["test_new.py"])
        assert state.test_files_revised == []


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

    def test_add_code_review(self, state):
        scores = {"confidence_score": 95, "quality_score": 92}
        state.add_code_review(scores)
        assert state.code_review_count == 1
        assert state.last_code_review["scores"] == scores
        assert state.last_code_review["status"] is None

    def test_set_last_code_review_status(self, state):
        state.add_code_review({"confidence_score": 95, "quality_score": 92})
        state.set_last_code_review_status("Pass")
        assert state.last_code_review["status"] == "Pass"

    def test_code_review_count(self, state):
        state.add_code_review({"confidence_score": 50, "quality_score": 50})
        state.add_code_review({"confidence_score": 95, "quality_score": 92})
        assert state.code_review_count == 2


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
