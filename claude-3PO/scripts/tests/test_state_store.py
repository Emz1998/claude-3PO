import json
import time

import pytest
from models.state import Agent
from helpers import make_hook_input
from lib.state_store import StateStore


class TestPhases:
    def test_add_phase(self, state):
        state.add_phase("explore")
        assert state.current_phase == "explore"
        assert state.get_phase_status("explore") == "in_progress"

    def test_set_phase_completed(self, state):
        state.add_phase("explore")
        state.set_phase_completed("explore")
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
        assert state.plan_revised is None

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

    def test_revision_tracking_lists(self, state):
        state.set_files_to_revise(["src/app.py", "src/utils.py"])
        state.add_file_revised("src/app.py")
        assert len(state.files_revised) == 1
        state.add_file_revised("src/utils.py")
        assert set(state.files_revised) == {"src/app.py", "src/utils.py"}

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

    def test_code_test_revision_tracking_lists(self, state):
        state.set_code_tests_to_revise(["test_app.py", "test_utils.py"])
        state.add_code_test_revised("test_app.py")
        assert len(state.code_tests_revised) == 1
        state.add_code_test_revised("test_utils.py")
        assert set(state.code_tests_revised) == {"test_app.py", "test_utils.py"}


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
        state.set_plan_file_path(".claude/plans/latest-plan.md")
        assert state.plan["file_path"] == ".claude/plans/latest-plan.md"

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

    def test_test_file_revision_tracking_lists(self, state):
        state.set_test_files_to_revise(["test_app.py", "test_utils.py"])
        state.add_test_file_revised("test_app.py")
        assert len(state.test_files_revised) == 1
        state.add_test_file_revised("test_utils.py")
        assert set(state.test_files_revised) == {"test_app.py", "test_utils.py"}

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


# ═══════════════════════════════════════════════════════════════════
# Clarify phase fields (headless_session_id + iteration_count)
# ═══════════════════════════════════════════════════════════════════


class TestClarifyPhaseFields:
    def test_get_clarify_phase_returns_none_initially(self, state):
        assert state.build.get_clarify_phase() is None

    def test_get_clarify_phase_returns_dict_after_add(self, state):
        state.add_phase("clarify")
        phase = state.build.get_clarify_phase()
        assert phase is not None
        assert phase["name"] == "clarify"
        assert phase["status"] == "in_progress"

    def test_set_clarify_session_persists_id(self, state):
        state.add_phase("clarify")
        state.build.set_clarify_session("sess_abc123")
        phase = state.build.get_clarify_phase()
        assert phase["headless_session_id"] == "sess_abc123"
        assert phase["iteration_count"] == 0

    def test_bump_clarify_iteration(self, state):
        state.add_phase("clarify")
        state.build.set_clarify_session("sess_abc123")
        state.build.bump_clarify_iteration()
        state.build.bump_clarify_iteration()
        phase = state.build.get_clarify_phase()
        assert phase["iteration_count"] == 2


# ═══════════════════════════════════════════════════════════════════
# Tasks (bulk setter)
# ═══════════════════════════════════════════════════════════════════


class TestTasksBulkSetter:
    def test_set_tasks(self, state):
        state.set_tasks(["Build auth", "Create schema", "Write API"])
        assert state.tasks == ["Build auth", "Create schema", "Write API"]

    def test_set_tasks_overwrites_existing(self, state):
        state.set_tasks(["Old task"])
        state.set_tasks(["New task 1", "New task 2"])
        assert state.tasks == ["New task 1", "New task 2"]

    def test_set_tasks_empty_list(self, state):
        state.set_tasks(["Something"])
        state.set_tasks([])
        assert state.tasks == []


# ═══════════════════════════════════════════════════════════════════
# JSONL — session isolation
# ═══════════════════════════════════════════════════════════════════


class TestSessionIsolation:
    def test_two_sessions_isolated(self, tmp_path):
        p = tmp_path / "state.jsonl"
        s1 = StateStore(p, session_id="session-1")
        s2 = StateStore(p, session_id="session-2")

        s1.add_phase("explore")
        s2.add_phase("plan")

        assert s1.current_phase == "explore"
        assert s2.current_phase == "plan"

    def test_session_delete_preserves_others(self, tmp_path):
        p = tmp_path / "state.jsonl"
        s1 = StateStore(p, session_id="session-1")
        s2 = StateStore(p, session_id="session-2")

        s1.add_phase("explore")
        s2.add_phase("plan")

        s1.delete()

        assert s1.current_phase == ""
        assert s2.current_phase == "plan"

    def test_reinitialize_replaces_session(self, tmp_path):
        p = tmp_path / "state.jsonl"
        s1 = StateStore(p, session_id="session-1")
        s1.add_phase("explore")
        s1.reinitialize({"phases": [{"name": "plan", "status": "in_progress"}]})
        assert s1.current_phase == "plan"

    def test_empty_file_returns_default(self, tmp_path):
        p = tmp_path / "state.jsonl"
        p.write_text("")
        default = {"session_id": "s1", "workflow_active": True}
        s = StateStore(p, session_id="s1", default_state=default)
        data = s.load()
        assert data.get("workflow_active") is True

    def test_nonexistent_file_returns_default(self, tmp_path):
        p = tmp_path / "state.jsonl"
        default = {"session_id": "s1", "value": 42}
        s = StateStore(p, session_id="s1", default_state=default)
        assert s.get("value") == 42


# ═══════════════════════════════════════════════════════════════════
# JSONL — cleanup_inactive
# ═══════════════════════════════════════════════════════════════════


class TestCleanupInactive:
    def test_removes_stale_sessions(self, tmp_path):
        p = tmp_path / "state.jsonl"
        old_ts = time.time() - 25 * 3600  # 25 hours ago
        recent_ts = time.time()

        lines = [
            json.dumps({"session_id": "old", "_last_updated": old_ts}),
            json.dumps({"session_id": "recent", "_last_updated": recent_ts}),
        ]
        p.write_text("\n".join(lines) + "\n")

        store = StateStore(p, session_id="any")
        removed = store.cleanup_inactive(max_age_hours=24)
        assert removed == 1

        s = StateStore(p, session_id="recent")
        assert s.get("session_id") == "recent"

        s_old = StateStore(p, session_id="old")
        assert s_old.get("session_id") is None

    def test_keeps_sessions_without_timestamp(self, tmp_path):
        p = tmp_path / "state.jsonl"
        lines = [
            json.dumps({"session_id": "no-ts"}),
        ]
        p.write_text("\n".join(lines) + "\n")

        store = StateStore(p, session_id="any")
        removed = store.cleanup_inactive(max_age_hours=24)
        assert removed == 0

    def test_empty_file_returns_zero(self, tmp_path):
        p = tmp_path / "state.jsonl"
        p.write_text("")
        store = StateStore(p, session_id="any")
        removed = store.cleanup_inactive(max_age_hours=24)
        assert removed == 0

    def test_nonexistent_file_returns_zero(self, tmp_path):
        p = tmp_path / "nonexistent.jsonl"
        store = StateStore(p, session_id="any")
        removed = store.cleanup_inactive(max_age_hours=24)
        assert removed == 0


# ═══════════════════════════════════════════════════════════════════
# Project tasks (implement workflow)
# ═══════════════════════════════════════════════════════════════════


class TestProjectTasks:
    def test_set_project_tasks(self, state):
        tasks = [
            {"id": "T-001", "title": "Build login", "subtasks": []},
            {"id": "T-002", "title": "Create schema", "subtasks": []},
        ]
        state.set_project_tasks(tasks)
        assert len(state.project_tasks) == 2
        assert state.project_tasks[0]["id"] == "T-001"

    def test_add_subtask(self, state):
        tasks = [{"id": "T-001", "title": "Build login", "subtasks": []}]
        state.set_project_tasks(tasks)
        state.add_subtask("T-001", "Implement login form")
        assert "Implement login form" in state.project_tasks[0]["subtasks"]

    def test_add_subtask_dedup(self, state):
        tasks = [{"id": "T-001", "title": "Build login", "subtasks": []}]
        state.set_project_tasks(tasks)
        state.add_subtask("T-001", "Implement login form")
        state.add_subtask("T-001", "Implement login form")
        assert state.project_tasks[0]["subtasks"].count("Implement login form") == 1

    def test_subtask_tracking_lists(self, state):
        tasks = [
            {"id": "T-001", "title": "Build login", "subtasks": []},
            {"id": "T-002", "title": "Create schema", "subtasks": []},
        ]
        state.set_project_tasks(tasks)
        assert len(state.project_tasks[0].get("subtasks", [])) == 0

        state.add_subtask("T-001", "Sub 1")
        assert len(state.project_tasks[0].get("subtasks", [])) == 1
        assert len(state.project_tasks[1].get("subtasks", [])) == 0

        state.add_subtask("T-002", "Sub 2")
        assert len(state.project_tasks[1].get("subtasks", [])) == 1


# ═══════════════════════════════════════════════════════════════════
# Plan files to modify (implement workflow)
# ═══════════════════════════════════════════════════════════════════


class TestPlanFilesToModify:
    def test_set_plan_files_to_modify(self, state):
        state.set_plan_files_to_modify(["src/app.py", "src/utils.py"])
        assert state.plan_files_to_modify == ["src/app.py", "src/utils.py"]

    def test_default_empty(self, state):
        assert state.plan_files_to_modify == []


class TestAgentRejectionCounter:
    def test_new_agent_has_zero_count(self, state):
        assert state.agent_rejection_count("tool-use-1") == 0

    def test_bump_increments_count(self, state):
        state.bump_agent_rejection_count("tool-use-1")
        state.bump_agent_rejection_count("tool-use-1")
        assert state.agent_rejection_count("tool-use-1") == 2

    def test_per_agent_id_isolated(self, state):
        state.bump_agent_rejection_count("a-1")
        state.bump_agent_rejection_count("a-2")
        state.bump_agent_rejection_count("a-1")
        assert state.agent_rejection_count("a-1") == 2
        assert state.agent_rejection_count("a-2") == 1

    def test_bump_returns_new_count(self, state):
        assert state.bump_agent_rejection_count("a-1") == 1
        assert state.bump_agent_rejection_count("a-1") == 2


class TestPhaseStatusHelpers:
    def test_is_phase_done_completed(self, state):
        state.add_phase("plan")
        state.set_phase_completed("plan")
        assert state.is_phase_done("plan") is True

    def test_is_phase_done_skipped(self, state):
        state.add_phase("plan", status="skipped")
        assert state.is_phase_done("plan") is True

    def test_is_phase_done_in_progress(self, state):
        state.add_phase("plan")
        assert state.is_phase_done("plan") is False

    def test_is_phase_done_absent(self, state):
        assert state.is_phase_done("plan") is False

    def test_done_phase_names_preserves_order(self, state):
        state.add_phase("explore")
        state.set_phase_completed("explore")
        state.add_phase("plan", status="skipped")
        state.add_phase("write-code")
        assert state.done_phase_names() == ["explore", "plan"]

    def test_done_phase_names_empty(self, state):
        assert state.done_phase_names() == []


class TestSetMany:
    def test_set_many_writes_all_fields(self, state):
        state.set_many({"status": "completed", "workflow_active": False})
        assert state.get("status") == "completed"
        assert state.get("workflow_active") is False

    def test_set_many_single_lock_acquire(self, state, tmp_path, monkeypatch):
        """Batched write should invoke update() exactly once, not per field."""
        call_count = {"n": 0}
        original = state.update

        def counting(fn):
            call_count["n"] += 1
            return original(fn)

        monkeypatch.setattr(state, "update", counting)
        state.set_many({"a": 1, "b": 2, "c": 3})
        assert call_count["n"] == 1

    def test_set_many_empty_dict_noop(self, state):
        state.set_many({})
        assert state.get("status") == "in_progress"
