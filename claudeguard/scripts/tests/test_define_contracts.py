"""Tests for define-contracts enforcement — file path guard + contract name validation."""

import pytest
from pathlib import Path
from models.state import Agent
from lib.extractors import extract_contract_names, extract_contract_files
from guardrails import write_guard
from utils.resolver import resolve_define_contracts
from helpers import make_hook_input


# ═══════════════════════════════════════════════════════════════════
# extract_contract_files — new extractor
# ═══════════════════════════════════════════════════════════════════


class TestExtractContractFiles:
    def test_extracts_from_table(self):
        content = (
            "# Contracts\n\n"
            "## Specifications\n\n"
            "| Name | Type | File | Description |\n"
            "|------|------|------|-------------|\n"
            "| UserService | class | src/services/user.py | User auth |\n"
            "| AuthProvider | interface | src/auth/provider.py | Token validation |\n"
        )
        files = extract_contract_files(content)
        assert files == ["src/services/user.py", "src/auth/provider.py"]

    def test_single_contract(self):
        content = (
            "# Contracts\n\n"
            "## Specifications\n\n"
            "| Name | Type | File | Description |\n"
            "|------|------|------|-------------|\n"
            "| DataStore | class | src/store.py | Persistence |\n"
        )
        files = extract_contract_files(content)
        assert files == ["src/store.py"]

    def test_empty_table(self):
        content = (
            "# Contracts\n\n"
            "## Specifications\n\n"
            "| Name | Type | File | Description |\n"
            "|------|------|------|-------------|\n"
        )
        files = extract_contract_files(content)
        assert files == []

    def test_no_section(self):
        content = "# Contracts\n\nSome text.\n"
        files = extract_contract_files(content)
        assert files == []


class TestExtractContractNamesWithFileColumn:
    """extract_contract_names should still work with the 4-column table."""

    def test_extracts_names(self):
        content = (
            "# Contracts\n\n"
            "## Specifications\n\n"
            "| Name | Type | File | Description |\n"
            "|------|------|------|-------------|\n"
            "| UserService | class | src/user.py | User auth |\n"
            "| AuthProvider | interface | src/auth.py | Token |\n"
        )
        names = extract_contract_names(content)
        assert names == ["UserService", "AuthProvider"]


# ═══════════════════════════════════════════════════════════════════
# Write guard — define-contracts only allows listed files
# ═══════════════════════════════════════════════════════════════════


class TestDefineContractsFileGuard:
    def _setup_state(self, state):
        state.set("workflow_type", "build")
        state.add_phase("define-contracts")
        state.set_contracts_names(["UserService", "AuthProvider"])
        state.set("contract_files", ["src/services/user.py", "src/auth/provider.py"])

    def test_listed_file_allowed(self, config, state):
        self._setup_state(state)
        hook = make_hook_input("Write", {"file_path": "src/services/user.py"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"

    def test_unlisted_file_blocked(self, config, state):
        self._setup_state(state)
        hook = make_hook_input("Write", {"file_path": "src/random.py"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "not in contracts" in msg.lower()

    def test_markdown_blocked(self, config, state):
        self._setup_state(state)
        hook = make_hook_input("Write", {"file_path": "notes.md"})
        decision, msg = write_guard(hook, config, state)
        assert decision == "block"
        assert "not in contracts" in msg.lower()

    def test_no_contract_files_falls_back_to_code_ext(self, config, state):
        """If no contract_files in state, fall back to code extension check."""
        state.set("workflow_type", "build")
        state.add_phase("define-contracts")
        hook = make_hook_input("Write", {"file_path": "src/anything.py"})
        decision, _ = write_guard(hook, config, state)
        assert decision == "allow"


# ═══════════════════════════════════════════════════════════════════
# Resolver — validates contract names in written files
# ═══════════════════════════════════════════════════════════════════


class TestResolveDefineContracts:
    def test_completes_when_all_contracts_found(self, tmp_path, state):
        state.set("workflow_type", "build")
        state.add_phase("define-contracts")
        state.set_contracts_names(["UserService"])
        state.set("contract_files", ["src/user.py"])
        state.set_contracts_written(True)

        # Write a file that contains the contract name
        code_file = tmp_path / "src" / "user.py"
        code_file.parent.mkdir(parents=True)
        code_file.write_text("class UserService:\n    pass\n")
        state.add_contract_code_file(str(code_file))

        resolve_define_contracts(state)
        assert state.contracts.get("validated") is True
        assert state.is_phase_completed("define-contracts")

    def test_does_not_complete_when_contract_missing(self, tmp_path, state):
        state.set("workflow_type", "build")
        state.add_phase("define-contracts")
        state.set_contracts_names(["UserService", "AuthProvider"])
        state.set("contract_files", ["src/user.py", "src/auth.py"])
        state.set_contracts_written(True)

        # Only write one file
        code_file = tmp_path / "src" / "user.py"
        code_file.parent.mkdir(parents=True)
        code_file.write_text("class UserService:\n    pass\n")
        state.add_contract_code_file(str(code_file))

        resolve_define_contracts(state)
        assert not state.is_phase_completed("define-contracts")

    def test_does_not_complete_when_not_written(self, state):
        state.set("workflow_type", "build")
        state.add_phase("define-contracts")
        resolve_define_contracts(state)
        assert not state.is_phase_completed("define-contracts")
