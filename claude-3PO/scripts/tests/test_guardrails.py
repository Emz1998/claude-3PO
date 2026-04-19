import pytest
from models.state import Agent
from handlers.guardrails import (
    write_guard,
    edit_guard,
    command_guard,
    agent_guard,
    webfetch_guard,
    phase_guard,
)
from helpers import make_hook_input, invoke_agent_report_guard as agent_report_guard


class TestWriteGuard:
    def test_allows_valid_write(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        content = "# Plan\n\n## Dependencies\n- flask\n\n## Tasks\n- Build login\n\n## Files to Modify\n\n| Action | Path |\n|--------|------|\n| Create | src/app.py |\n"
        hook = make_hook_input("Write", {"file_path": ".claude/plans/latest-plan.md", "content": content})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_blocks_invalid_write(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Write", {"file_path": "anything.py"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "block"

    def test_blank_phase_shows_readable_fallback(self, config, state):
        """Bug: pre-phase writes produced 'in phase: ' with a blank suffix."""
        hook = make_hook_input("Write", {"file_path": "random.py"})
        decision, message = write_guard(hook, config, state)
        assert decision == "block"
        assert "in phase:" in message
        assert "in phase: " not in message or "(no phase" in message


class TestEditGuard:
    def test_allows_valid_edit(self, config, state):
        state.add_phase("plan-review")
        hook = make_hook_input("Edit", {"file_path": ".claude/plans/latest-plan.md"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "allow"

    def test_blocks_invalid_edit(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Edit", {"file_path": "anything.py"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "block"

    def test_blank_phase_shows_readable_fallback(self, config, state):
        hook = make_hook_input("Edit", {"file_path": "CLAUDE.md"})
        decision, message = edit_guard(hook, config, state)
        assert decision == "block"
        assert "(no phase" in message


class TestCommandGuard:
    def test_allows_read_only_in_explore(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Bash", {"command": "ls -la"})
        decision, _ = command_guard(hook, config, state)
        assert decision == "allow"

    def test_blocks_non_read_only_in_explore(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Bash", {"command": "rm -rf /"})
        decision, _ = command_guard(hook, config, state)
        assert decision == "block"


class TestAgentGuard:
    def test_allows_correct_agent(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Agent", {"subagent_type": "Explore"})
        decision, _ = agent_guard(hook, config, state)
        assert decision == "allow"

    def test_blocks_wrong_agent(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Agent", {"subagent_type": "WrongAgent"})
        decision, _ = agent_guard(hook, config, state)
        assert decision == "block"

    def test_blank_phase_shows_readable_fallback(self, config, state):
        hook = make_hook_input("Agent", {"subagent_type": "Research"})
        decision, message = agent_guard(hook, config, state)
        assert decision == "block"
        assert "(no phase" in message


class TestWebfetchGuard:
    def test_allows_safe_domain(self, config, state):
        hook = make_hook_input("WebFetch", {"url": "https://docs.python.org/3/"})
        decision, _ = webfetch_guard(hook, config, state)
        assert decision == "allow"

    def test_blocks_unsafe_domain(self, config, state):
        hook = make_hook_input("WebFetch", {"url": "https://evil.com"})
        decision, _ = webfetch_guard(hook, config, state)
        assert decision == "block"


class TestPhaseGuard:
    def test_allows_valid_transition(self, config, state):
        state.add_phase("explore")
        state.set_phase_completed("explore")
        hook = make_hook_input("Skill", {"skill": "research"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "allow"

    def test_blocks_when_not_completed(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Skill", {"skill": "plan"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "block"

    def test_blocks_reinvoking_completed_phase(self, config, state):
        """Bug #2: re-invoking a completed phase must be blocked with a clear message."""
        state.set("workflow_type", "specs")
        state.add_phase("vision")
        state.set_phase_completed("vision")
        hook = make_hook_input("Skill", {"skill": "vision"})
        decision, message = phase_guard(hook, config, state)
        assert decision == "block"
        assert "vision" in message.lower()
        # Message should not read just "Already in 'vision' phase" when the phase
        # is actually already completed — that's misleading. It should mention the
        # re-invocation is not allowed in either state.
        assert "re-invoke" in message.lower() or "already" in message.lower()

    def test_blocks_backward_navigation_from_next_phase(self, config, state):
        """Bug #2: /vision from a later phase must stay blocked."""
        state.set("workflow_type", "specs")
        state.add_phase("vision")
        state.set_phase_completed("vision")
        state.add_phase("strategy")
        state.set_phase_completed("strategy")
        hook = make_hook_input("Skill", {"skill": "vision"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "block"


class TestAgentReportGuard:
    # --- Block: invalid content, nothing recorded ---

    def test_blocks_empty_report(self, config, state):
        state.add_phase("plan-review")
        hook = {"last_assistant_message": ""}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "block"
        assert state.plan_review_count == 0

    def test_blocks_missing_scores(self, config, state):
        state.add_phase("code-review")
        hook = {"last_assistant_message": "Looks good overall."}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "block"
        assert state.code_review_count == 0

    def test_blocks_code_review_missing_sections(self, config, state):
        state.add_phase("code-review")
        hook = {"last_assistant_message": "Confidence: 50\nQuality: 50"}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "block"
        assert state.code_review_count == 0
        assert state.files_to_revise == []

    def test_blocks_code_review_empty_files_section(self, config, state):
        state.add_phase("code-review")
        hook = {"last_assistant_message": (
            "Confidence: 50\nQuality: 50\n\n"
            "## Files to revise\n\n"
            "## Tests to revise\n- test_app.py\n"
        )}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "block"
        assert state.code_review_count == 0

    def test_blocks_test_review_missing_files_section(self, config, state):
        state.add_phase("test-review")
        hook = {"last_assistant_message": "Some feedback.\nFail"}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "block"
        assert state.test_review_count == 0

    # --- Allow: valid content, everything recorded ---

    def test_allows_valid_code_review(self, config, state):
        state.add_phase("code-review")
        hook = {"last_assistant_message": (
            "Confidence: 50\nQuality: 50\n\n"
            "## Files to revise\n- src/app.py\n\n"
            "## Tests to revise\n- test_app.py\n"
        )}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "allow"
        assert state.code_review_count == 1
        assert state.files_to_revise == ["src/app.py"]
        assert state.code_tests_to_revise == ["test_app.py"]

    def test_allows_valid_plan_review(self, config, state):
        state.add_phase("plan-review")
        hook = {"last_assistant_message": "Confidence: 95\nQuality: 92"}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "allow"
        assert state.plan_review_count == 1
        assert state.last_plan_review["status"] == "Pass"

    def test_allows_valid_test_review(self, config, state):
        state.add_phase("test-review")
        hook = {"last_assistant_message": (
            "Tests need work.\n\n"
            "## Files to revise\n- test_app.py\n\n"
            "Fail"
        )}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "allow"
        assert state.test_review_count == 1
        assert state.test_files_to_revise == ["test_app.py"]

    def test_passing_code_review_no_sections_needed(self, config, state):
        state.add_phase("code-review")
        hook = {"last_assistant_message": (
            "Confidence: 95\nQuality: 95\n\n"
            "## Files to revise\n- src/app.py\n\n"
            "## Tests to revise\n- test_app.py\n"
        )}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "allow"
        assert state.last_code_review["status"] == "Pass"


class TestStateFileEditInTestMode:
    def test_allows_state_edit_in_test_mode(self, config, state):
        state.set("test_mode", True)
        state.add_phase("vision")
        hook = make_hook_input("Edit", {"file_path": "scripts/state.jsonl"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "allow"

    def test_blocks_state_edit_outside_test_mode(self, config, state):
        state.add_phase("vision")
        hook = make_hook_input("Edit", {"file_path": "scripts/state.jsonl"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "block"

    def test_allows_state_write_in_test_mode(self, config, state):
        state.set("test_mode", True)
        state.add_phase("strategy")
        hook = make_hook_input("Write", {"file_path": "scripts/state.jsonl"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_blocks_state_write_outside_test_mode(self, config, state):
        state.add_phase("strategy")
        hook = make_hook_input("Write", {"file_path": "scripts/state.jsonl"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "block"
