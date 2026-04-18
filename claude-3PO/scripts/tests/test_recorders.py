"""Tests for the 19-method Recorder state API + the thin facade dispatch."""

import pytest

from utils.recorder import Recorder
from helpers import make_hook_input


# ── Artifacts: plan ─────────────────────────────────────────────────


class TestRecordPlan:
    def test_partial_update_file_path(self, state):
        Recorder(state).record_plan(file_path=".claude/plans/p.md")
        assert state.plan["file_path"] == ".claude/plans/p.md"
        assert state.plan.get("written", False) is False

    def test_partial_update_written(self, state):
        Recorder(state).record_plan(written=True)
        assert state.plan["written"] is True

    def test_partial_update_revised(self, state):
        Recorder(state).record_plan(revised=True)
        assert state.plan_revised is True

    def test_replace_reviews(self, state):
        Recorder(state).record_plan(
            reviews=[{"iteration": 1, "scores": {"c": 80}, "status": "Pass"}]
        )
        assert state.plan_reviews == [
            {"iteration": 1, "scores": {"c": 80}, "status": "Pass"}
        ]

    def test_no_args_is_noop(self, state):
        before = state.plan
        Recorder(state).record_plan()
        assert state.plan == before


# ── Artifacts: tests ────────────────────────────────────────────────


class TestRecordTests:
    def test_file_paths_add_dedups(self, state):
        rec = Recorder(state)
        rec.record_tests(file_paths=("add", ["t_a.py"]))
        rec.record_tests(file_paths=("add", ["t_a.py", "t_b.py"]))
        assert state.tests["file_paths"] == ["t_a.py", "t_b.py"]

    def test_file_paths_replace(self, state):
        rec = Recorder(state)
        rec.record_tests(file_paths=("add", ["t_a.py"]))
        rec.record_tests(file_paths=("replace", ["t_c.py"]))
        assert state.tests["file_paths"] == ["t_c.py"]

    def test_executed_flag(self, state):
        Recorder(state).record_tests(executed=True)
        assert state.tests["executed"] is True

    def test_files_to_revise_replace(self, state):
        Recorder(state).record_tests(files_to_revise=("replace", ["t_x.py"]))
        assert state.test_files_to_revise == ["t_x.py"]

    def test_files_revised_add_dedups(self, state):
        rec = Recorder(state)
        rec.record_tests(files_revised=("add", ["t_a.py"]))
        rec.record_tests(files_revised=("add", ["t_a.py"]))
        assert state.test_files_revised == ["t_a.py"]


# ── Artifacts: code_files ───────────────────────────────────────────


class TestRecordCodeFiles:
    def test_file_paths_add_dedups(self, state):
        rec = Recorder(state)
        rec.record_code_files(file_paths=("add", ["a.py"]))
        rec.record_code_files(file_paths=("add", ["a.py", "b.py"]))
        assert state.code_files["file_paths"] == ["a.py", "b.py"]

    def test_file_paths_replace(self, state):
        rec = Recorder(state)
        rec.record_code_files(file_paths=("add", ["a.py"]))
        rec.record_code_files(file_paths=("replace", ["c.py"]))
        assert state.code_files["file_paths"] == ["c.py"]

    def test_files_to_revise_replace(self, state):
        Recorder(state).record_code_files(files_to_revise=("replace", ["z.py"]))
        assert state.files_to_revise == ["z.py"]

    def test_files_revised_add_dedups(self, state):
        rec = Recorder(state)
        rec.record_code_files(files_revised=("add", ["a.py"]))
        rec.record_code_files(files_revised=("add", ["a.py"]))
        assert state.files_revised == ["a.py"]


# ── Artifacts: report ───────────────────────────────────────────────


class TestRecordReportWritten:
    def test_written_only(self, state):
        Recorder(state).record_report_written(written=True)
        assert state.report_written is True

    def test_path_only(self, state):
        Recorder(state).record_report_written(file_path="r.md")
        assert state.load().get("report_file_path") == "r.md"

    def test_both(self, state):
        Recorder(state).record_report_written(file_path="r.md", written=True)
        assert state.load().get("report_file_path") == "r.md"
        assert state.report_written is True


# ── Session / workflow metadata ─────────────────────────────────────


class TestRecordCommand:
    def test_appends(self, state):
        rec = Recorder(state)
        rec.record_command("pytest")
        rec.record_command("ls")
        assert state.load().get("commands") == ["pytest", "ls"]


class TestRecordSessionId:
    def test_sets(self, state):
        Recorder(state).record_session_id("sess-42")
        entries = state._read_all_lines()
        assert any(e.get("session_id") == "sess-42" for e in entries)


class TestRecordStoryId:
    def test_sets(self, state):
        Recorder(state).record_story_id("US-9")
        assert state.load().get("story_id") == "US-9"


class TestRecordWorkflowType:
    def test_sets(self, state):
        Recorder(state).record_workflow_type("implement")
        assert state.load().get("workflow_type") == "implement"


class TestRecordWorkflowActive:
    def test_sets(self, state):
        Recorder(state).record_workflow_active(False)
        assert state.load().get("workflow_active") is False


class TestRecordWorkflowStatus:
    def test_sets(self, state):
        Recorder(state).record_workflow_status("completed")
        assert state.load().get("status") == "completed"


class TestRecordWorkflowConvenience:
    def test_all_three(self, state):
        Recorder(state).record_workflow(
            type="build", active=False, status="completed"
        )
        d = state.load()
        assert d["workflow_type"] == "build"
        assert d["workflow_active"] is False
        assert d["status"] == "completed"

    def test_partial(self, state):
        Recorder(state).record_workflow(status="in_progress")
        assert state.load().get("status") == "in_progress"


# ── Lifecycle / flags ───────────────────────────────────────────────


class TestRecordTestMode:
    def test_sets(self, state):
        Recorder(state).record_test_mode("e2e")
        assert state.load().get("test_mode") == "e2e"


class TestRecordPhase:
    def test_default_in_progress(self, state):
        Recorder(state).record_phase("plan")
        assert state.current_phase == "plan"
        assert state.get_phase_status("plan") == "in_progress"

    def test_with_status(self, state):
        Recorder(state).record_phase("plan", status="completed")
        assert state.get_phase_status("plan") == "completed"

    def test_multiple_appends(self, state):
        rec = Recorder(state)
        rec.record_phase("plan")
        rec.record_phase("write-code")
        names = [p["name"] for p in state.phases]
        assert names == ["plan", "write-code"]


class TestRecordTdd:
    def test_sets(self, state):
        Recorder(state).record_tdd(True)
        assert state.load().get("tdd") is True


class TestRecordValidationResult:
    def test_appends_pass(self, state):
        Recorder(state).record_validation_result("pass")
        assert state.load().get("validations") == [{"result": "pass"}]

    def test_appends_fail(self, state):
        rec = Recorder(state)
        rec.record_validation_result("pass")
        rec.record_validation_result("fail")
        assert state.load().get("validations") == [
            {"result": "pass"}, {"result": "fail"}
        ]


# ── Agents / reviews / tasks ────────────────────────────────────────


class TestRecordAgent:
    def test_appends(self, state):
        Recorder(state).record_agent("Plan", "in_progress", "tu_1")
        a = state.get_agent("Plan")
        assert a is not None
        assert a["tool_use_id"] == "tu_1"
        assert a["status"] == "in_progress"


class TestRecordCodeReview:
    def test_appends_with_status(self, state):
        Recorder(state).record_code_review(
            iteration=1, scores={"confidence_score": 95, "quality_score": 90},
            status="Pass",
        )
        last = state.last_code_review
        assert last["iteration"] == 1
        assert last["scores"]["confidence_score"] == 95
        assert last["status"] == "Pass"

    def test_appends_without_status(self, state):
        Recorder(state).record_code_review(iteration=2, scores={"c": 50})
        assert state.last_code_review["status"] is None


class TestRecordTestReview:
    def test_appends_with_status(self, state):
        Recorder(state).record_test_review(
            iteration=1, verdict="Pass", status="Pass"
        )
        last = state.last_test_review
        assert last["iteration"] == 1
        assert last["verdict"] == "Pass"
        assert last["status"] == "Pass"

    def test_appends_without_status(self, state):
        Recorder(state).record_test_review(iteration=1, verdict="Fail")
        assert state.last_test_review["status"] is None


class TestRecordTask:
    def test_top_level(self, state):
        Recorder(state).record_task("T-1", "Build login", "Do the login bits")
        ptasks = state.implement.project_tasks
        assert len(ptasks) == 1
        assert ptasks[0]["task_id"] == "T-1"
        assert ptasks[0]["subject"] == "Build login"
        assert ptasks[0]["description"] == "Do the login bits"
        assert ptasks[0].get("parent_task_id") is None

    def test_with_parent(self, state):
        rec = Recorder(state)
        rec.record_task("T-1", "Parent", "parent body")
        rec.record_task("T-1.1", "Sub", "child body", parent_task_id="T-1")
        ptasks = state.implement.project_tasks
        assert len(ptasks) == 2
        assert ptasks[1]["parent_task_id"] == "T-1"

    def test_dedup_by_task_id(self, state):
        rec = Recorder(state)
        rec.record_task("T-1", "Subject A", "desc")
        rec.record_task("T-1", "Subject B", "desc2")
        assert len(state.implement.project_tasks) == 1


# ── Facade dispatch ─────────────────────────────────────────────────


class TestRecordFacade:
    def test_unknown_tool_noop(self, state, config):
        Recorder(state).record({"tool_name": "Mystery"}, config)
        assert state.phases == []

    def test_skill_routes_to_phase(self, state, config):
        hook = make_hook_input("Skill", {"skill": "plan"})
        Recorder(state).record(hook, config)
        assert state.current_phase == "plan"

    def test_bash_routes_to_command(self, state, config):
        hook = make_hook_input("Bash", {"command": "echo hi"})
        Recorder(state).record(hook, config)
        assert state.load().get("commands") == ["echo hi"]

    def test_write_in_plan_phase_records_plan(self, state, config):
        state.add_phase("plan")
        hook = make_hook_input(
            "Write",
            {"file_path": config.plan_file_path, "content": "# plan"},
        )
        Recorder(state).record(hook, config)
        assert state.plan["written"] is True
        assert state.plan["file_path"].endswith(config.plan_file_path)

    def test_write_in_write_tests_phase_records_tests(self, state, config):
        state.add_phase("write-tests")
        hook = make_hook_input("Write", {"file_path": "tests/test_a.py"})
        Recorder(state).record(hook, config)
        assert "tests/test_a.py" in state.tests["file_paths"]

    def test_write_in_write_code_phase_records_code(self, state, config):
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "src/app.py"})
        Recorder(state).record(hook, config)
        assert "src/app.py" in state.code_files["file_paths"]

    def test_write_in_write_report_phase_records_report(self, state, config):
        state.add_phase("write-report")
        hook = make_hook_input("Write", {"file_path": "r.md"})
        Recorder(state).record(hook, config)
        assert state.report_written is True
        assert state.load().get("report_file_path") == "r.md"

    def test_edit_in_plan_review_marks_plan_revised(self, state, config):
        state.add_phase("plan-review")
        hook = make_hook_input("Edit", {"file_path": "anything.md"})
        Recorder(state).record(hook, config)
        assert state.plan_revised is True

    def test_edit_in_test_review_records_test_revision(self, state, config):
        state.add_phase("test-review")
        hook = make_hook_input("Edit", {"file_path": "tests/test_a.py"})
        Recorder(state).record(hook, config)
        assert "tests/test_a.py" in state.test_files_revised

    def test_edit_in_code_review_records_file_revision(self, state, config):
        state.add_phase("code-review")
        state.add_code_file("src/app.py")
        hook = make_hook_input("Edit", {"file_path": "src/app.py"})
        Recorder(state).record(hook, config)
        assert "src/app.py" in state.files_revised
