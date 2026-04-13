import json
import pytest
from models.state import Agent
from pathlib import Path
from utils.recorder import (
    record_file_write,
    record_agent_start,
    record_phase_transition,
    record_test_execution,
    record_test_review_result,
    record_plan_review_scores,
    record_code_review_scores,
    record_scores,
    record_pr_create_output,
    record_ci_check_output,
    record_phase_completion,
    record_agent_completion,
    inject_plan_metadata,
)
from utils.initializer import parse_frontmatter
from helpers import make_hook_input


class TestRecordFileWrite:
    def test_plan_phase(self, state):
        state.add_phase("plan")
        hook = make_hook_input("Write", {"file_path": ".claude/plans/latest-plan.md"})
        record_file_write(hook, state)
        assert state.plan["file_path"] == ".claude/plans/latest-plan.md"
        assert state.plan["written"] is True

    def test_write_tests_phase(self, state):
        state.add_phase("write-tests")
        hook = make_hook_input("Write", {"file_path": "test_app.py"})
        record_file_write(hook, state)
        assert "test_app.py" in state.tests["file_paths"]

    def test_write_code_phase(self, state):
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "app.py"})
        record_file_write(hook, state)
        assert "app.py" in state.code_files["file_paths"]

    def test_write_report_phase(self, state):
        state.add_phase("write-report")
        hook = make_hook_input("Write", {"file_path": "report.md"})
        record_file_write(hook, state)
        assert state.report_written is True


class TestRecordAgentStart:
    def test_adds_agent_with_id(self, state):
        record_agent_start("Explore", "agent-001", state)
        assert state.count_agents("Explore") == 1
        agent = state.get_agent("Explore")
        assert agent["tool_use_id"] == "agent-001"
        assert agent["status"] == "in_progress"


class TestRecordPhaseTransition:
    def test_completes_current_and_starts_next(self, state):
        state.add_phase("explore")
        record_phase_transition("research", state)
        assert state.is_phase_completed("explore")
        assert state.current_phase == "research"
        assert state.get_phase_status("research") == "in_progress"

    def test_first_phase(self, state):
        record_phase_transition("explore", state)
        assert state.current_phase == "explore"


class TestRecordTestExecution:
    def test_marks_executed(self, state):
        record_test_execution(state)
        assert state.tests["executed"] is True


class TestRecordTestReviewResult:
    def test_pass(self, state):
        record_test_review_result("Pass", state)
        assert state.last_test_review["verdict"] == "Pass"

    def test_fail(self, state):
        record_test_review_result("Fail", state)
        assert state.last_test_review["verdict"] == "Fail"

    def test_multiple_reviews(self, state):
        record_test_review_result("Fail", state)
        record_test_review_result("Pass", state)
        assert state.test_review_count == 2


class TestRecordScores:
    def test_plan_review(self, state):
        scores = {"confidence_score": 85, "quality_score": 90}
        record_scores("plan-review", scores, state)
        assert state.last_plan_review["scores"] == scores

    def test_code_review(self, state):
        scores = {"confidence_score": 95, "quality_score": 92}
        record_scores("code-review", scores, state)
        assert state.last_code_review["scores"] == scores


class TestRecordPrCreateOutput:
    def test_valid_json(self, state):
        output = json.dumps({"number": 42, "url": "https://github.com/org/repo/pull/42"})
        record_pr_create_output(output, state)
        assert state.pr_number == 42
        assert state.pr_status == "created"

    def test_invalid_json(self, state):
        with pytest.raises(ValueError, match="parse"):
            record_pr_create_output("not json", state)

    def test_missing_number(self, state):
        with pytest.raises(ValueError, match="number"):
            record_pr_create_output(json.dumps({"url": "https://github.com"}), state)


class TestRecordCiCheckOutput:
    def test_all_success(self, state):
        output = json.dumps([
            {"name": "build", "conclusion": "SUCCESS"},
            {"name": "lint", "conclusion": "SUCCESS"},
        ])
        record_ci_check_output(output, state)
        assert state.ci_status == "passed"
        assert len(state.ci_results) == 2

    def test_has_failure(self, state):
        output = json.dumps([
            {"name": "build", "conclusion": "SUCCESS"},
            {"name": "test", "conclusion": "FAILURE"},
        ])
        record_ci_check_output(output, state)
        assert state.ci_status == "failed"

    def test_pending(self, state):
        output = json.dumps([
            {"name": "build", "conclusion": "SUCCESS"},
            {"name": "test", "conclusion": None},
        ])
        record_ci_check_output(output, state)
        assert state.ci_status == "pending"


class TestRecordPhaseCompletion:
    def test_completes_phase(self, state):
        state.add_phase("explore")
        record_phase_completion("explore", state)
        assert state.is_phase_completed("explore")


class TestRecordAgentCompletion:
    def test_marks_completed_by_id(self, state):
        state.add_agent(Agent(name="Explore", status="in_progress", tool_use_id="agent-001"))
        record_agent_completion("agent-001", state)
        agent = state.get_agent("Explore")
        assert agent["status"] == "completed"

    def test_completes_correct_agent(self, state):
        state.add_agent(Agent(name="Explore", status="in_progress", tool_use_id="agent-001"))
        state.add_agent(Agent(name="Explore", status="in_progress", tool_use_id="agent-002"))
        record_agent_completion("agent-002", state)
        agents = [a for a in state.agents if a["name"] == "Explore"]
        assert agents[0]["status"] == "in_progress"
        assert agents[1]["status"] == "completed"


class TestInjectPlanMetadata:
    def test_injects_frontmatter(self, tmp_path, state):
        state.set("session_id", "test-sess-123")
        state.set("workflow_type", "implement")
        state.set("story_id", "SK-001")

        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# My Plan\n\nSome content.")

        inject_plan_metadata(str(plan_file), state)

        content = plan_file.read_text()
        fm = parse_frontmatter(content)
        assert fm["session_id"] == "test-sess-123"
        assert fm["workflow_type"] == "implement"
        assert fm["story_id"] == "SK-001"
        assert "date" in fm
        assert "# My Plan" in content

    def test_replaces_existing_frontmatter(self, tmp_path, state):
        state.set("session_id", "new-sess")
        state.set("workflow_type", "build")

        plan_file = tmp_path / "plan.md"
        plan_file.write_text("---\nsession_id: old-sess\n---\n# Plan")

        inject_plan_metadata(str(plan_file), state)

        content = plan_file.read_text()
        fm = parse_frontmatter(content)
        assert fm["session_id"] == "new-sess"
        assert "old-sess" not in content

    def test_nonexistent_file_does_nothing(self, tmp_path, state):
        inject_plan_metadata(str(tmp_path / "nope.md"), state)  # no error


# ═══════════════════════════════════════════════════════════════════
# record_plan_sections — auto-parse deps + tasks from plan
# ═══════════════════════════════════════════════════════════════════


class TestRecordPlanSections:
    def test_extracts_deps_and_tasks(self, tmp_path, state):
        from utils.recorder import record_plan_sections

        plan_file = tmp_path / "plan.md"
        plan_file.write_text(
            "# Plan\n\n"
            "## Dependencies\n- flask\n- pytest\n\n"
            "## Contracts\n- UserService\n\n"
            "## Tasks\n- Build login\n- Write tests\n"
        )
        record_plan_sections(str(plan_file), state)
        assert state.dependencies["packages"] == ["flask", "pytest"]
        assert state.tasks == ["Build login", "Write tests"]

    def test_empty_sections(self, tmp_path, state):
        from utils.recorder import record_plan_sections

        plan_file = tmp_path / "plan.md"
        plan_file.write_text(
            "# Plan\n\n## Dependencies\n\n## Contracts\n\n## Tasks\n\n"
        )
        record_plan_sections(str(plan_file), state)
        assert state.dependencies["packages"] == []
        assert state.tasks == []

    def test_nonexistent_file_does_nothing(self, tmp_path, state):
        from utils.recorder import record_plan_sections

        record_plan_sections(str(tmp_path / "nope.md"), state)
        assert state.dependencies["packages"] == []
        assert state.tasks == []


# ═══════════════════════════════════════════════════════════════════
# record_contracts_file — extract contract names from contracts.md
# ═══════════════════════════════════════════════════════════════════


class TestRecordContractsFile:
    def test_extracts_contract_names(self, tmp_path, state):
        from utils.recorder import record_contracts_file

        contracts_file = tmp_path / "latest-contracts.md"
        contracts_file.write_text(
            "# Contracts\n\n- UserService\n- AuthProvider\n- DatabaseClient\n"
        )
        record_contracts_file(str(contracts_file), state)
        assert state.contracts["file_path"] == str(contracts_file)
        assert state.contract_names == ["UserService", "AuthProvider", "DatabaseClient"]

    def test_empty_contracts_file(self, tmp_path, state):
        from utils.recorder import record_contracts_file

        contracts_file = tmp_path / "latest-contracts.md"
        contracts_file.write_text("# Contracts\n\nNo bullet items here.\n")
        record_contracts_file(str(contracts_file), state)
        assert state.contract_names == []

    def test_nonexistent_file_does_nothing(self, tmp_path, state):
        from utils.recorder import record_contracts_file

        record_contracts_file(str(tmp_path / "nope.md"), state)
        assert state.contract_names == []


# ═══════════════════════════════════════════════════════════════════
# record_dependency_install
# ═══════════════════════════════════════════════════════════════════


class TestRecordDependencyInstall:
    def test_marks_installed(self, state):
        from utils.recorder import record_dependency_install

        record_dependency_install("npm install", state)
        assert state.dependencies["installed"] is True


# ═══════════════════════════════════════════════════════════════════
# record_file_write — define-contracts phase
# ═══════════════════════════════════════════════════════════════════


class TestRecordFileWriteDefineContracts:
    def test_records_contract_code_file(self, state):
        state.add_phase("define-contracts")
        hook = make_hook_input("Write", {"file_path": "src/interfaces.py"})
        record_file_write(hook, state)
        assert "src/interfaces.py" in state.contracts["code_files"]
        assert state.contracts["written"] is True

    def test_records_multiple_code_files(self, state):
        state.add_phase("define-contracts")
        hook1 = make_hook_input("Write", {"file_path": "src/interfaces.py"})
        hook2 = make_hook_input("Write", {"file_path": "src/types.ts"})
        record_file_write(hook1, state)
        record_file_write(hook2, state)
        assert "src/interfaces.py" in state.contracts["code_files"]
        assert "src/types.ts" in state.contracts["code_files"]
