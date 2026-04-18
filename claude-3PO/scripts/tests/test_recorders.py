"""Tests for recording logic — state mutations after tool use."""

import json
import pytest
from models.state import Agent
from pathlib import Path
from lib.parser import parse_frontmatter
from utils.recorder import Recorder
from helpers import make_hook_input


class TestRecordFileWrite:
    """Tests for write_guard._record_file_write (via state setters)."""

    def test_plan_phase(self, state):
        state.add_phase("plan")
        state.set_plan_file_path(".claude/plans/latest-plan.md")
        state.set_plan_written(True)
        assert state.plan["file_path"] == ".claude/plans/latest-plan.md"
        assert state.plan["written"] is True

    def test_write_tests_phase(self, state):
        state.add_phase("write-tests")
        state.add_test_file("test_app.py")
        assert "test_app.py" in state.tests["file_paths"]

    def test_write_code_phase(self, state):
        state.add_phase("write-code")
        state.add_code_file("app.py")
        assert "app.py" in state.code_files["file_paths"]

    def test_write_report_phase(self, state):
        state.add_phase("write-report")
        state.set_report_written(True)
        assert state.report_written is True


class TestRecordAgentStart:
    def test_adds_agent_with_id(self, state):
        state.add_agent(Agent(name="Explore", status="in_progress", tool_use_id="agent-001"))
        assert state.count_agents("Explore") == 1
        agent = state.get_agent("Explore")
        assert agent["tool_use_id"] == "agent-001"
        assert agent["status"] == "in_progress"


class TestRecordPhaseTransition:
    def test_completes_current_and_starts_next(self, state):
        state.add_phase("explore")
        state.set_phase_completed("explore")
        state.add_phase("research")
        assert state.is_phase_completed("explore")
        assert state.current_phase == "research"
        assert state.get_phase_status("research") == "in_progress"

    def test_first_phase(self, state):
        state.add_phase("explore")
        assert state.current_phase == "explore"


class TestRecordTestExecution:
    def test_marks_executed(self, state):
        state.set_tests_executed(True)
        assert state.tests["executed"] is True


class TestRecordTestReviewResult:
    def test_pass(self, state):
        state.add_test_review("Pass")
        assert state.last_test_review["verdict"] == "Pass"

    def test_fail(self, state):
        state.add_test_review("Fail")
        assert state.last_test_review["verdict"] == "Fail"

    def test_multiple_reviews(self, state):
        state.add_test_review("Fail")
        state.add_test_review("Pass")
        assert state.test_review_count == 2


class TestRecordScores:
    def test_plan_review(self, state):
        scores = {"confidence_score": 85, "quality_score": 90}
        state.add_plan_review(scores)
        assert state.last_plan_review["scores"] == scores

    def test_code_review(self, state):
        scores = {"confidence_score": 95, "quality_score": 92}
        state.add_code_review(scores)
        assert state.last_code_review["scores"] == scores


class TestRecordPrCreateOutput:
    def test_valid_json(self, state):
        recorder = Recorder(state)
        output = json.dumps({"number": 42, "url": "https://github.com/org/repo/pull/42"})
        recorder.record_pr_create(output)
        assert state.pr_number == 42
        assert state.pr_status == "created"

    def test_invalid_json(self, state):
        recorder = Recorder(state)
        with pytest.raises(ValueError, match="parse"):
            recorder.record_pr_create("not json")

    def test_missing_number(self, state):
        recorder = Recorder(state)
        with pytest.raises(ValueError, match="number"):
            recorder.record_pr_create(json.dumps({"url": "https://github.com"}))


class TestRecordCiCheckOutput:
    def test_all_success(self, state):
        recorder = Recorder(state)
        output = json.dumps([
            {"name": "build", "conclusion": "SUCCESS"},
            {"name": "lint", "conclusion": "SUCCESS"},
        ])
        recorder.record_ci_check(output)
        assert state.ci_status == "passed"
        assert len(state.ci_results) == 2

    def test_has_failure(self, state):
        recorder = Recorder(state)
        output = json.dumps([
            {"name": "build", "conclusion": "SUCCESS"},
            {"name": "test", "conclusion": "FAILURE"},
        ])
        recorder.record_ci_check(output)
        assert state.ci_status == "failed"

    def test_pending(self, state):
        recorder = Recorder(state)
        output = json.dumps([
            {"name": "build", "conclusion": "SUCCESS"},
            {"name": "test", "conclusion": None},
        ])
        recorder.record_ci_check(output)
        assert state.ci_status == "pending"


class TestRecordPhaseCompletion:
    def test_completes_phase(self, state):
        state.add_phase("explore")
        state.set_phase_completed("explore")
        assert state.is_phase_completed("explore")


class TestRecordAgentCompletion:
    def test_marks_completed_by_id(self, state):
        state.add_agent(Agent(name="Explore", status="in_progress", tool_use_id="agent-001"))
        state.update_agent_status("agent-001", "completed")
        agent = state.get_agent("Explore")
        assert agent["status"] == "completed"

    def test_completes_correct_agent(self, state):
        state.add_agent(Agent(name="Explore", status="in_progress", tool_use_id="agent-001"))
        state.add_agent(Agent(name="Explore", status="in_progress", tool_use_id="agent-002"))
        state.update_agent_status("agent-002", "completed")
        agents = [a for a in state.agents if a["name"] == "Explore"]
        assert agents[0]["status"] == "in_progress"
        assert agents[1]["status"] == "completed"


class TestInjectPlanMetadata:
    def test_injects_frontmatter(self, tmp_path, state):
        recorder = Recorder(state)
        state.set("workflow_type", "implement")
        state.set("story_id", "SK-001")

        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# My Plan\n\nSome content.")

        recorder.record_plan_metadata(str(plan_file))

        content = plan_file.read_text()
        fm = parse_frontmatter(content)
        assert fm["session_id"] == "test-session"
        assert fm["workflow_type"] == "implement"
        assert fm["story_id"] == "SK-001"
        assert "date" in fm
        assert "# My Plan" in content

    def test_replaces_existing_frontmatter(self, tmp_path, state):
        recorder = Recorder(state)
        state.set("workflow_type", "build")

        plan_file = tmp_path / "plan.md"
        plan_file.write_text("---\nsession_id: old-sess\n---\n# Plan")

        recorder.record_plan_metadata(str(plan_file))

        content = plan_file.read_text()
        fm = parse_frontmatter(content)
        assert fm["session_id"] == "test-session"
        assert "old-sess" not in content


class TestRecordPlanSections:
    def test_extracts_tasks_and_files(self, tmp_path, state):
        recorder = Recorder(state)
        plan = tmp_path / "plan.md"
        plan.write_text(
            "# Plan\n\n"
            "## Tasks\n- Build login\n- Create schema\n\n"
            "## Files to Modify\n\n| Action | Path |\n|--------|------|\n| Create | src/app.py |\n"
        )
        recorder.record_plan_sections(str(plan))
        assert state.tasks == ["Build login", "Create schema"]
        assert "src/app.py" in state.code_files_to_write

    def test_missing_file_noop(self, state):
        recorder = Recorder(state)
        recorder.record_plan_sections("/nonexistent/plan.md")
        assert state.tasks == []

    def test_empty_sections(self, tmp_path, state):
        recorder = Recorder(state)
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\n## Tasks\n")
        recorder.record_plan_sections(str(plan))
        assert state.tasks == []
