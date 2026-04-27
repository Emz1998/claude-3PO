import pytest
from models.state import Agent
from handlers.guardrails import (
    phase_guard,
    command_guard,
    write_guard,
    edit_guard,
    agent_guard,
    webfetch_guard,
)
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


# ── File Write ─────────────────────────────────────────────────────


class TestIsFileWriteAllowed:
    def test_plan_correct_path(self, config, state):
        state.set("workflow_type", "implement")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        content = (
            "# Plan\n\n"
            "## Context\nWhy.\n\n"
            "## Approach\nHow.\n\n"
            "## Files to Create/Modify\n- src/app.py\n\n"
            "## Verification\n- run tests\n"
        )
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
        state.set("workflow_type", "implement")
        state.implement.set_plan_files_to_modify(["app.py"])
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "app.py"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_write_code_invalid_ext(self, config, state):
        state.set("workflow_type", "implement")
        state.implement.set_plan_files_to_modify(["app.py"])
        state.add_phase("write-code")
        hook = make_hook_input("Write", {"file_path": "readme.md"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"

    def test_non_writable_phase(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Write", {"file_path": "anything.py"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg


# ── File Edit ──────────────────────────────────────────────────────


class TestIsFileEditAllowed:
    def test_plan_phase_correct_path(self, config, state):
        state.add_phase("plan")
        hook = make_hook_input("Edit", {"file_path": ".claude/plans/latest-plan.md"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "allow"

    def test_plan_phase_wrong_path(self, config, state):
        state.add_phase("plan")
        hook = make_hook_input("Edit", {"file_path": "wrong.md"})
        decision, msg = edit_guard(hook, config, state)
        assert decision == "block"
        assert "not allowed" in msg

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


# ═══════════════════════════════════════════════════════════════════
# Plan content validation — required sections
# ═══════════════════════════════════════════════════════════════════


class TestPlanContentValidation:
    """Plan Write must include implement-workflow required sections."""

    @pytest.fixture(autouse=True)
    def _set_implement_workflow(self, state):
        state.set("workflow_type", "implement")

    def _plan_content(self, context=True, approach=True, files=True, verification=True):
        parts = ["# Implementation Plan\n"]
        if context:
            parts.append("## Context\n\nWhy.\n")
        if approach:
            parts.append("## Approach\n\nHow.\n")
        if files:
            parts.append("## Files to Create/Modify\n- src/app.py\n")
        if verification:
            parts.append("## Verification\n- run tests\n")
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

    def test_plan_write_missing_context_blocked(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._plan_content(context=False),
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Context" in msg

    def test_plan_write_missing_approach_blocked(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._plan_content(approach=False),
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Approach" in msg

    def test_plan_write_missing_files_blocked(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._plan_content(files=False),
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Files to Create/Modify" in msg

    def test_plan_write_missing_verification_blocked(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._plan_content(verification=False),
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Verification" in msg

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
