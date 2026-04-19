"""Tests for implement plan template validation and file extraction."""

import pytest
from models.state import Agent
from handlers.guardrails import write_guard
from lib.extractors import extract_plan_files_to_modify
from helpers import make_hook_input


# ═══════════════════════════════════════════════════════════════════
# Implement plan content validation
# ═══════════════════════════════════════════════════════════════════


class TestImplementPlanValidation:
    """Implement plan must have: Context, Approach, Files to Create/Modify, Verification."""

    def _impl_plan(self, context=True, approach=True, files=True, verification=True):
        parts = ["# Implementation Plan\n"]
        if context:
            parts.append("## Context\n\nSome context.\n")
        if approach:
            parts.append("## Approach\n\nSome approach.\n")
        if files:
            parts.append("## Files to Create/Modify\n\n| Action | Path |\n|--------|------|\n| Create | src/app.py |\n")
        if verification:
            parts.append("## Verification\n\nRun tests.\n")
        return "\n".join(parts)

    def test_all_sections_allowed(self, config, state):
        state.set("workflow_type", "implement")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._impl_plan(),
        })
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_missing_context_blocked(self, config, state):
        state.set("workflow_type", "implement")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._impl_plan(context=False),
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Context" in msg

    def test_missing_approach_blocked(self, config, state):
        state.set("workflow_type", "implement")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._impl_plan(approach=False),
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Approach" in msg

    def test_missing_files_blocked(self, config, state):
        state.set("workflow_type", "implement")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._impl_plan(files=False),
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Files to Create/Modify" in msg

    def test_missing_verification_blocked(self, config, state):
        state.set("workflow_type", "implement")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": self._impl_plan(verification=False),
        })
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "Verification" in msg

    def test_build_plan_still_validates_build_format(self, config, state):
        """Build plan requires Dependencies, Tasks, Files to Modify."""
        state.set("workflow_type", "build")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        content = "# Plan\n\n## Dependencies\n- flask\n\n## Tasks\n- Build login\n\n## Files to Modify\n\n| Action | Path |\n|--------|------|\n| Create | src/app.py |\n"
        hook = make_hook_input("Write", {
            "file_path": ".claude/plans/latest-plan.md",
            "content": content,
        })
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"


# ═══════════════════════════════════════════════════════════════════
# extract_plan_files_to_modify
# ═══════════════════════════════════════════════════════════════════


class TestExtractPlanFilesToModify:
    def test_extracts_from_table(self):
        content = (
            "## Files to Create/Modify\n\n"
            "| Action | Path |\n"
            "|--------|------|\n"
            "| Create | src/app.py |\n"
            "| Modify | src/utils.py |\n"
        )
        files = extract_plan_files_to_modify(content)
        assert files == ["src/app.py", "src/utils.py"]

    def test_empty_table_returns_empty(self):
        content = "## Files to Create/Modify\n\nNo files.\n"
        files = extract_plan_files_to_modify(content)
        assert files == []

    def test_no_section_returns_empty(self):
        content = "## Context\n\nSome text.\n"
        files = extract_plan_files_to_modify(content)
        assert files == []

    def test_single_file(self):
        content = (
            "## Files to Create/Modify\n\n"
            "| Action | Path |\n"
            "|--------|------|\n"
            "| Create | src/main.py |\n"
        )
        files = extract_plan_files_to_modify(content)
        assert files == ["src/main.py"]
