import pytest
from models.state import Agent
from guardrails import (
    write_guard,
    edit_guard,
    command_guard,
    agent_guard,
    webfetch_guard,
    phase_guard,
)
from helpers import make_hook_input


class TestWriteGuard:
    def test_allows_valid_write(self, config, state):
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {"file_path": ".claude/plans/plan.md"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_blocks_invalid_write(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Write", {"file_path": "anything.py"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "block"


class TestEditGuard:
    def test_allows_valid_edit(self, config, state):
        state.add_phase("plan-review")
        hook = make_hook_input("Edit", {"file_path": ".claude/plans/plan.md"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "allow"

    def test_blocks_invalid_edit(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Edit", {"file_path": "anything.py"})
        decision, _ = edit_guard(hook, config, state)
        assert decision == "block"


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
        state.complete_phase("explore")
        hook = make_hook_input("Skill", {"skill": "research"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "allow"

    def test_blocks_when_not_completed(self, config, state):
        state.add_phase("explore")
        hook = make_hook_input("Skill", {"skill": "plan"})
        decision, _ = phase_guard(hook, config, state)
        assert decision == "block"
