import pytest
from models.state import Agent
from guardrails import (
    phase_guard,
    command_guard,
    write_guard,
    edit_guard,
    agent_guard,
    webfetch_guard,
)
from guardrails.agent_report_guard import AgentReportGuard
from helpers import make_hook_input


# ── Phase ──────────────────────────────────────────────────────────


class TestIsPhaseAllowed:
    def test_explore_to_research_parallel(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Skill", {"skill": "research"})
        decision, msg = phase_guard(hook, config, state)
        assert decision == "allow"
        assert "parallel" in msg.lower()

    def test_blocks_when_current_not_completed(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Skill", {"skill": "plan"})
        decision, msg = phase_guard(hook, config, state)
        assert decision == "block"
        assert "not completed" in msg

    def test_valid_transition(self, config, state):
        state.add_phase("explore")
        state.set_phase_completed("explore")
        hook = make_hook_input("Skill", {"skill": "research"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "allow"


# ── Command ────────────────────────────────────────────────────────


class TestIsCommandAllowed:
    def test_read_only_phase_allows_ls(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Bash", {"command": "ls -la"})
        decision, _ = command_guard(hook, config, state)
        assert decision == "allow"

    def test_read_only_phase_blocks_rm(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Bash", {"command": "rm -rf /"})
        decision, msg = command_guard(hook, config, state)
        assert decision == "block"
        assert "read-only" in msg

    def test_pr_create_needs_json_flag(self, config, state):
        state.add_phase("pr-create")
        hook = make_hook_input("Bash", {"command": "gh pr create --title test"})
        decision, msg = command_guard(hook, config, state)
        assert decision == "block"
        assert "--json" in msg

    def test_pr_create_with_json_passes(self, config, state):
        state.add_phase("pr-create")
        hook = make_hook_input("Bash", {"command": "gh pr create --json number"})
        decision, _ = command_guard(hook, config, state)
        assert decision == "allow"

    def test_ci_check_needs_json_flag(self, config, state):
        state.add_phase("ci-check")
        hook = make_hook_input("Bash", {"command": "gh pr checks"})
        decision, msg = command_guard(hook, config, state)
        assert decision == "block"
        assert "--json" in msg


# ── File Write ─────────────────────────────────────────────────────


class TestIsFileWriteAllowed:
    def test_plan_correct_path(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        content = "# Plan\n\n## Dependencies\n- flask\n\n## Tasks\n- Build login\n\n## Files to Modify\n\n| Action | Path |\n|--------|------|\n| Create | src/app.py |\n"
        hook = make_hook_input("Write", {"file_path": ".claude/plans/latest-plan.md", "content": content})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_plan_wrong_path(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {"file_path": "wrong.md"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg

    def test_plan_blocks_before_agent(self, config, state):
        state.add_phase("plan")
        hook = make_hook_input("Write", {"file_path": ".claude/plans/latest-plan.md"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Plan agent must be invoked first" in msg

    def test_write_tests_valid_suffix_pattern(self, config, state):
        state.add_phase("write-tests")
        hook = make_hook_input("Write", {"file_path": "app.test.ts"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_write_tests_valid_prefix_pattern(self, config, state):
        state.add_phase("write-tests")
        hook = make_hook_input("Write", {"file_path": "app_test.py"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_write_tests_invalid_pattern(self, config, state):
        state.add_phase("write-tests")
        hook = make_hook_input("Write", {"file_path": "app.txt"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg

    def test_write_code_valid_ext(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "app.py"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_write_code_invalid_ext(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "readme.md"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg

    def test_non_writable_phase(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Write", {"file_path": "anything.py"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg


# ── File Edit ──────────────────────────────────────────────────────


class TestIsFileEditAllowed:
    def test_plan_review_correct_path(self, config, state):
        state.add_phase("plan-review")
        hook = make_hook_input("Edit", {"file_path": ".claude/plans/latest-plan.md"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "allow"

    def test_plan_review_wrong_path(self, config, state):
        state.add_phase("plan-review")
        hook = make_hook_input("Edit", {"file_path": "wrong.md"})
        decision, msg = edit_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg

    def test_test_review_valid_file(self, config, state):
        state.add_phase("test-review")
        state.add_test_file("test_app.py")
        hook = make_hook_input("Edit", {"file_path": "test_app.py"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "allow"

    def test_test_review_unknown_file(self, config, state):
        state.add_phase("test-review")
        hook = make_hook_input("Edit", {"file_path": "unknown.py"})
        decision, msg = edit_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg

    def test_code_review_valid_file(self, config, state):
        state.add_phase("code-review")
        state.add_code_file("app.py")
        hook = make_hook_input("Edit", {"file_path": "app.py"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "allow"

    def test_code_review_blocks_code_edit_before_tests_revised(self, config, state):
        state.add_phase("code-review")
        state.add_code_file("app.py")
        state.set_code_tests_to_revise(["test_app.py"])
        state.set_files_to_revise(["app.py"])
        hook = make_hook_input("Edit", {"file_path": "app.py"})
        decision, msg = edit_guard(hook, config, state)
        assert decision == "block"
        assert "test files" in msg.lower()

    def test_code_review_allows_code_edit_after_tests_revised(self, config, state):
        state.add_phase("code-review")
        state.add_code_file("app.py")
        state.set_code_tests_to_revise(["test_app.py"])
        state.set_files_to_revise(["app.py"])
        state.add_code_test_revised("test_app.py")
        hook = make_hook_input("Edit", {"file_path": "app.py"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "allow"

    def test_code_review_allows_test_edit(self, config, state):
        state.add_phase("code-review")
        state.add_test_file("test_app.py")
        state.set_code_tests_to_revise(["test_app.py"])
        hook = make_hook_input("Edit", {"file_path": "test_app.py"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "allow"

    def test_non_editable_phase(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Edit", {"file_path": "anything.py"})
        decision, msg = edit_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg


# ── Agent ──────────────────────────────────────────────────────────


class TestIsAgentAllowed:
    def test_correct_agent(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Agent", {"subagent_type": "Explore"})
        decision, _ = agent_guard(hook, config, state)
        assert decision == "allow"

    def test_wrong_agent(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Agent", {"subagent_type": "WrongAgent"})
        decision, msg = agent_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg

    def test_research_parallel_with_explore(self, config, state):
        state.add_phase("explore")
        state.add_agent(Agent(name="Explore", status="in_progress"))
        hook = make_hook_input("Agent", {"subagent_type": "Research"})
        decision, msg = agent_guard(hook, config, state)
        assert decision == "allow"
        assert "parallel" in msg.lower()

    def test_agent_at_max(self, config, state):
        state.add_phase("explore")
        for _ in range(3):
            state.add_agent(Agent(name="Explore", status="completed"))
        hook = make_hook_input("Agent", {"subagent_type": "Explore"})
        decision, msg = agent_guard(hook, config, state)
        assert decision == "block"
        assert "max" in msg.lower()

    def test_plan_review_blocked_without_revision(self, config, state):
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_plan_review_status("Fail")
        state.set_plan_revised(False)
        hook = make_hook_input("Agent", {"subagent_type": "PlanReview"})
        decision, msg = agent_guard(hook, config, state)
        assert decision == "block"
        assert "revised" in msg.lower()

    def test_plan_review_allowed_after_revision(self, config, state):
        state.add_phase("plan-review")
        state.add_plan_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_plan_review_status("Fail")
        state.set_plan_revised(True)
        hook = make_hook_input("Agent", {"subagent_type": "PlanReview"})
        decision, _ = agent_guard(hook, config, state)
        assert decision == "allow"

    def test_code_review_blocked_without_revision(self, config, state):
        state.add_phase("code-review")
        state.set_files_to_revise(["src/app.py"])
        state.add_code_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_code_review_status("Fail")
        hook = make_hook_input("Agent", {"subagent_type": "CodeReviewer"})
        decision, msg = agent_guard(hook, config, state)
        assert decision == "block"
        assert "revised" in msg.lower()

    def test_code_review_allowed_after_revision(self, config, state):
        state.add_phase("code-review")
        state.set_files_to_revise(["src/app.py"])
        state.add_code_review({"confidence_score": 50, "quality_score": 50})
        state.set_last_code_review_status("Fail")
        state.add_file_revised("src/app.py")
        hook = make_hook_input("Agent", {"subagent_type": "CodeReviewer"})
        decision, _ = agent_guard(hook, config, state)
        assert decision == "allow"

    def test_test_review_blocked_without_revision(self, config, state):
        state.add_phase("test-review")
        state.add_test_review("Fail")
        state.set_test_files_to_revise(["test_app.py"])
        hook = make_hook_input("Agent", {"subagent_type": "TestReviewer"})
        decision, msg = agent_guard(hook, config, state)
        assert decision == "block"
        assert "revised" in msg.lower()

    def test_test_review_allowed_after_revision(self, config, state):
        state.add_phase("test-review")
        state.add_test_review("Fail")
        state.set_test_files_to_revise(["test_app.py"])
        state.add_test_file_revised("test_app.py")
        hook = make_hook_input("Agent", {"subagent_type": "TestReviewer"})
        decision, _ = agent_guard(hook, config, state)
        assert decision == "allow"

    def test_no_agent_required(self, config, state):
        state.add_phase("write-code")
        hook = make_hook_input("Agent", {"subagent_type": "SomeAgent"})
        decision, msg = agent_guard(hook, config, state)
        assert decision == "block"
        assert "No agent allowed" in msg


# ── WebFetch ───────────────────────────────────────────────────────


class TestIsWebfetchAllowed:
    def test_safe_domain(self, config, state):
        hook = make_hook_input("WebFetch", {"url": "https://docs.python.org/3/"})
        decision, _ = webfetch_guard(hook, config, state)
        assert decision == "allow"

    def test_unsafe_domain(self, config, state):
        hook = make_hook_input("WebFetch", {"url": "https://evil.com/data"})
        decision, msg = webfetch_guard(hook, config, state)
        assert decision == "block"
        assert "not in the safe domains" in msg

    def test_empty_url(self, config, state):
        hook = make_hook_input("WebFetch", {"url": ""})
        decision, msg = webfetch_guard(hook, config, state)
        assert decision == "block"
        assert "empty" in msg.lower()

    def test_subdomain_allowed(self, config, state):
        hook = make_hook_input("WebFetch", {"url": "https://api.github.com/repos"})
        decision, _ = webfetch_guard(hook, config, state)
        assert decision == "allow"


# ── Scores ─────────────────────────────────────────────────────────


class TestScoresValid:
    def test_valid_scores(self):
        extractor = lambda c: {"confidence_score": 85, "quality_score": 90}
        ok, scores = AgentReportGuard.scores_valid("any content", extractor)
        assert ok is True
        assert scores["confidence_score"] == 85

    def test_missing_scores(self):
        extractor = lambda c: {"confidence_score": None, "quality_score": None}
        with pytest.raises(ValueError, match="required"):
            AgentReportGuard.scores_valid("any content", extractor)

    def test_out_of_range(self):
        extractor = lambda c: {"confidence_score": 150, "quality_score": 90}
        with pytest.raises(ValueError, match="between 1 and 100"):
            AgentReportGuard.scores_valid("any content", extractor)


# ── Verdict ────────────────────────────────────────────────────────


class TestVerdictValid:
    def test_pass(self):
        ok, verdict = AgentReportGuard.verdict_valid("Pass", lambda c: c)
        assert ok is True
        assert verdict == "Pass"

    def test_fail(self):
        ok, verdict = AgentReportGuard.verdict_valid("Fail", lambda c: c)
        assert ok is True
        assert verdict == "Fail"

    def test_invalid(self):
        with pytest.raises(ValueError, match="Pass.+Fail"):
            AgentReportGuard.verdict_valid("Maybe", lambda c: c)


# ── Agent Report ───────────────────────────────────────────────────


class TestIsAgentReportValid:
    def test_plan_review_with_scores(self, config, state):
        state.add_phase("plan-review")
        hook = {"last_assistant_message": "Confidence: 85\nQuality: 90"}
        guard = AgentReportGuard(hook, config, state)
        msg = guard._validate_report()
        assert "scores present" in msg

    def test_test_review_with_verdict(self, config, state):
        state.add_phase("test-review")
        hook = {"last_assistant_message": "Pass"}
        guard = AgentReportGuard(hook, config, state)
        msg = guard._validate_report()
        assert "verdict present" in msg

    def test_empty_report(self, config, state):
        state.add_phase("plan-review")
        hook = {"last_assistant_message": ""}
        guard = AgentReportGuard(hook, config, state)
        with pytest.raises(ValueError, match="empty"):
            guard._validate_report()

    def test_non_review_phase(self, config, state):
        state.add_phase("explore")
        hook = {"last_assistant_message": "something"}
        guard = AgentReportGuard(hook, config, state)
        with pytest.raises(ValueError, match="does not require"):
            guard._validate_report()


class TestValidateReviewSections:
    def test_code_review_fail_requires_files_to_revise(self, state):
        state.add_phase("code-review")
        content = "Confidence: 50\nQuality: 50\n\nSome feedback."
        with pytest.raises(ValueError, match="Files to revise"):
            AgentReportGuard.validate_review_sections(content, "code-review")

    def test_code_review_fail_requires_tests_to_revise(self, state):
        state.add_phase("code-review")
        content = (
            "Confidence: 50\nQuality: 50\n\n"
            "## Files to revise\n- src/app.py\n"
        )
        with pytest.raises(ValueError, match="Tests to revise"):
            AgentReportGuard.validate_review_sections(content, "code-review")

    def test_code_review_with_both_sections(self, state):
        state.add_phase("code-review")
        content = (
            "Confidence: 50\nQuality: 50\n\n"
            "## Files to revise\n- src/app.py\n\n"
            "## Tests to revise\n- test_app.py\n"
        )
        files, tests = AgentReportGuard.validate_review_sections(content, "code-review")
        assert files == ["src/app.py"]
        assert tests == ["test_app.py"]

    def test_code_review_empty_files_section_blocked(self, state):
        state.add_phase("code-review")
        content = (
            "Confidence: 50\nQuality: 50\n\n"
            "## Files to revise\n\n"
            "## Tests to revise\n- test_app.py\n"
        )
        with pytest.raises(ValueError, match="Files to revise.*empty"):
            AgentReportGuard.validate_review_sections(content, "code-review")

    def test_code_review_empty_tests_section_blocked(self, state):
        state.add_phase("code-review")
        content = (
            "Confidence: 50\nQuality: 50\n\n"
            "## Files to revise\n- src/app.py\n\n"
            "## Tests to revise\n\n"
        )
        with pytest.raises(ValueError, match="Tests to revise.*empty"):
            AgentReportGuard.validate_review_sections(content, "code-review")

    def test_test_review_fail_requires_files_to_revise(self, state):
        state.add_phase("test-review")
        content = "Some feedback.\nFail"
        with pytest.raises(ValueError, match="Files to revise"):
            AgentReportGuard.validate_review_sections(content, "test-review")

    def test_test_review_with_files_section(self, state):
        state.add_phase("test-review")
        content = (
            "Some feedback.\n\n"
            "## Files to revise\n- test_app.py\n\n"
            "Fail"
        )
        files, tests = AgentReportGuard.validate_review_sections(content, "test-review")
        assert files == ["test_app.py"]
        assert tests == []

    def test_plan_review_no_sections_required(self, state):
        state.add_phase("plan-review")
        content = "Confidence: 50\nQuality: 50"
        files, tests = AgentReportGuard.validate_review_sections(content, "plan-review")
        assert files == []
        assert tests == []


# ═══════════════════════════════════════════════════════════════════
# Plan content validation — required sections
# ═══════════════════════════════════════════════════════════════════


class TestPlanContentValidation:
    """Plan Write must include ## Dependencies, ## Tasks, ## Files to Modify sections (build workflow)."""

    @pytest.fixture(autouse=True)
    def _set_build_workflow(self, state):
        state.set("workflow_type", "build")

    _FILES_TABLE = "## Files to Modify\n\n| Action | Path |\n|--------|------|\n| Create | src/app.py |\n"

    def _plan_content(self, deps=True, tasks=True, files=True):
        parts = ["# Implementation Plan\n"]
        if deps:
            parts.append("## Dependencies\n- flask\n")
        if tasks:
            parts.append("## Tasks\n- Build login\n")
        if files:
            parts.append(self._FILES_TABLE)
        return "\n".join(parts)

    def test_plan_write_with_all_sections_allowed(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._plan_content(),
        })
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_plan_write_missing_dependencies_blocked(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._plan_content(deps=False),
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Dependencies" in msg

    def test_plan_write_missing_tasks_blocked(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._plan_content(tasks=False),
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Tasks" in msg

    def test_plan_write_missing_files_to_modify_blocked(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._plan_content(files=False),
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Files to Modify" in msg

    def test_plan_write_missing_all_sections_blocked(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": "# Plan\n\nSome content without sections.\n",
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "missing required sections" in msg

    def test_plan_tasks_as_subsections_blocked(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        content = (
            "# Plan\n\n"
            "## Dependencies\n- flask\n\n"
            "## Tasks\n\n"
            "### Task 1: Build login\n"
            "Some description.\n\n"
            "### Task 2: Create schema\n"
            "Some description.\n\n"
            + self._FILES_TABLE
        )
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": content,
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Tasks" in msg and "bullet" in msg

    def test_plan_deps_as_subsections_blocked(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        content = (
            "# Plan\n\n"
            "## Dependencies\n\n"
            "### Python packages\n- flask\n\n"
            "## Tasks\n- Build login\n\n"
            + self._FILES_TABLE
        )
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": content,
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Dependencies" in msg and "bullet" in msg

    def test_plan_tasks_empty_bullets_blocked(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        content = (
            "# Plan\n\n"
            "## Dependencies\n- flask\n\n"
            "## Tasks\n\nSome prose but no bullet items.\n\n"
            + self._FILES_TABLE
        )
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": content,
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Tasks" in msg and "bullet" in msg


# ═══════════════════════════════════════════════════════════════════
# Plan edit — section preservation
# ═══════════════════════════════════════════════════════════════════


class TestPlanEditSectionPreservation:
    """Plan Edit in plan-review must not remove ## Dependencies, ## Tasks, ## Files to Modify (build workflow)."""

    _VALID_PLAN = "# Plan\n\n## Dependencies\n- flask\n\n## Tasks\n- Build login\n\n## Files to Modify\n\n| Action | Path |\n|--------|------|\n| Create | src/app.py |\n"

    @pytest.fixture(autouse=True)
    def _set_build_workflow(self, state):
        state.set("workflow_type", "build")

    def test_edit_preserving_sections_allowed(self, config, state, tmp_path, monkeypatch):
        plan_file = tmp_path / "latest-plan.md"
        plan_file.write_text(self._VALID_PLAN)
        monkeypatch.setattr(type(config), "plan_file_path", property(lambda self: str(plan_file)))
        state.add_phase("plan-review")
        hook = make_hook_input("Edit", {
            "file_path": str(plan_file),
            "old_string": "- Build login",
            "new_string": "- Build login page with OAuth",
        })
        decision, _ = edit_guard(hook, config, state)
        assert decision == "allow"

    def test_edit_removing_dependencies_blocked(self, config, state, tmp_path, monkeypatch):
        plan_file = tmp_path / "latest-plan.md"
        plan_file.write_text(self._VALID_PLAN)
        monkeypatch.setattr(type(config), "plan_file_path", property(lambda self: str(plan_file)))
        state.add_phase("plan-review")
        hook = make_hook_input("Edit", {
            "file_path": str(plan_file),
            "old_string": "## Dependencies\n- flask\n",
            "new_string": "",
        })
        decision, msg = edit_guard(hook, config, state)
        assert decision == "block"
        assert "Dependencies" in msg

    def test_edit_removing_tasks_blocked(self, config, state, tmp_path, monkeypatch):
        plan_file = tmp_path / "latest-plan.md"
        plan_file.write_text(self._VALID_PLAN)
        monkeypatch.setattr(type(config), "plan_file_path", property(lambda self: str(plan_file)))
        state.add_phase("plan-review")
        hook = make_hook_input("Edit", {
            "file_path": str(plan_file),
            "old_string": "## Tasks\n- Build login\n",
            "new_string": "",
        })
        decision, msg = edit_guard(hook, config, state)
        assert decision == "block"
        assert "Tasks" in msg


# ═══════════════════════════════════════════════════════════════════
# Install-deps file write — package manager files only
# ═══════════════════════════════════════════════════════════════════


class TestInstallDepsFileWrite:
    def test_package_json_allowed(self, config, state):
        state.add_phase("install-deps")
        hook = make_hook_input("Write", {"file_path": "package.json"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_requirements_txt_allowed(self, config, state):
        state.add_phase("install-deps")
        hook = make_hook_input("Write", {"file_path": "requirements.txt"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_pyproject_toml_allowed(self, config, state):
        state.add_phase("install-deps")
        hook = make_hook_input("Write", {"file_path": "pyproject.toml"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_go_mod_allowed(self, config, state):
        state.add_phase("install-deps")
        hook = make_hook_input("Write", {"file_path": "go.mod"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_cargo_toml_allowed(self, config, state):
        state.add_phase("install-deps")
        hook = make_hook_input("Write", {"file_path": "Cargo.toml"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_gemfile_allowed(self, config, state):
        state.add_phase("install-deps")
        hook = make_hook_input("Write", {"file_path": "Gemfile"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_pipfile_allowed(self, config, state):
        state.add_phase("install-deps")
        hook = make_hook_input("Write", {"file_path": "Pipfile"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_random_file_blocked(self, config, state):
        state.add_phase("install-deps")
        hook = make_hook_input("Write", {"file_path": "app.py"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg

    def test_markdown_blocked(self, config, state):
        state.add_phase("install-deps")
        hook = make_hook_input("Write", {"file_path": "readme.md"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg


# ═══════════════════════════════════════════════════════════════════
# Define-contracts file write — code extensions only
# ═══════════════════════════════════════════════════════════════════


class TestDefineContractsFileWrite:
    def test_python_file_allowed(self, config, state):
        state.add_phase("define-contracts")
        hook = make_hook_input("Write", {"file_path": "src/interfaces.py"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_typescript_file_allowed(self, config, state):
        state.add_phase("define-contracts")
        hook = make_hook_input("Write", {"file_path": "src/types.ts"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_markdown_blocked(self, config, state):
        state.add_phase("define-contracts")
        hook = make_hook_input("Write", {"file_path": "readme.md"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg

    def test_text_file_blocked(self, config, state):
        state.add_phase("define-contracts")
        hook = make_hook_input("Write", {"file_path": "notes.txt"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg


# ═══════════════════════════════════════════════════════════════════
# Plan Write — contracts file allowed during plan phase
# ═══════════════════════════════════════════════════════════════════


class TestPlanWriteContractsFile:
    def test_contracts_file_allowed_in_plan_phase(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/contracts/latest-contracts.md",
            "content": "# Contracts\n\n- UserService\n",
        })
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"


# ═══════════════════════════════════════════════════════════════════
# Install-deps command validation
# ═══════════════════════════════════════════════════════════════════


class TestInstallDepsCommandAllowed:
    def test_npm_install_allowed(self, config, state):
        state.add_phase("install-deps")
        hook = make_hook_input("Bash", {"command": "npm install"})
        decision, _ = command_guard(hook, config, state)
        assert decision == "allow"
