"""Tests for contracts template enforcement and name extraction from table."""

import pytest
from models.state import Agent
from utils.extractors import extract_contract_names
from utils.validators import is_file_write_allowed
from helpers import make_hook_input


# ═══════════════════════════════════════════════════════════════════
# extract_contract_names — table-based extraction
# ═══════════════════════════════════════════════════════════════════


class TestExtractContractNamesFromTable:
    def test_extracts_from_table(self):
        content = (
            "# Contracts\n\n"
            "## Specifications\n\n"
            "| Name | Type | Description |\n"
            "|------|------|-------------|\n"
            "| UserService | class | User auth |\n"
            "| AuthProvider | interface | Token validation |\n"
        )
        names = extract_contract_names(content)
        assert names == ["UserService", "AuthProvider"]

    def test_single_contract(self):
        content = (
            "# Contracts\n\n"
            "## Specifications\n\n"
            "| Name | Type | Description |\n"
            "|------|------|-------------|\n"
            "| DataStore | class | Persistence layer |\n"
        )
        names = extract_contract_names(content)
        assert names == ["DataStore"]

    def test_empty_table_returns_empty(self):
        content = (
            "# Contracts\n\n"
            "## Specifications\n\n"
            "| Name | Type | Description |\n"
            "|------|------|-------------|\n"
        )
        names = extract_contract_names(content)
        assert names == []

    def test_no_table_no_bullets_returns_empty(self):
        content = "# Contracts\n\nSome text with no structure.\n"
        names = extract_contract_names(content)
        assert names == []

    def test_bullet_fallback_still_works(self):
        """Backward compat: bullets still work if no table."""
        content = "- UserService\n- AuthProvider\n"
        names = extract_contract_names(content)
        assert names == ["UserService", "AuthProvider"]


# ═══════════════════════════════════════════════════════════════════
# Contracts content validation (guardrail)
# ═══════════════════════════════════════════════════════════════════


class TestContractsContentValidation:
    """Contracts file must have ## Specifications section with a table."""

    def _valid_contracts(self):
        return (
            "# Contracts\n\n"
            "## Specifications\n\n"
            "| Name | Type | Description |\n"
            "|------|------|-------------|\n"
            "| UserService | class | User auth |\n"
        )

    def test_valid_contracts_allowed(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/contracts/latest-contracts.md",
            "content": self._valid_contracts(),
        })
        ok, _ = is_file_write_allowed(hook, config, state)
        assert ok is True

    def test_missing_specifications_blocked(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/contracts/latest-contracts.md",
            "content": "# Contracts\n\nJust some text.\n",
        })
        with pytest.raises(ValueError, match="Specifications"):
            is_file_write_allowed(hook, config, state)

    def test_empty_table_blocked(self, config, state):
        state.set("workflow_type", "build")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        content = (
            "# Contracts\n\n"
            "## Specifications\n\n"
            "| Name | Type | Description |\n"
            "|------|------|-------------|\n"
        )
        hook = make_hook_input("Write", {
            "file_path": ".claude/contracts/latest-contracts.md",
            "content": content,
        })
        with pytest.raises(ValueError, match="at least one contract"):
            is_file_write_allowed(hook, config, state)

    def test_implement_skips_contracts_validation(self, config, state):
        """Implement workflow doesn't write contracts — but if it did, no validation."""
        state.set("workflow_type", "implement")
        state.add_phase("plan")
        state.add_agent(Agent(name="Plan", status="completed", tool_use_id="p-1"))
        hook = make_hook_input("Write", {
            "file_path": ".claude/contracts/latest-contracts.md",
            "content": "- None",
        })
        ok, _ = is_file_write_allowed(hook, config, state)
        assert ok is True
