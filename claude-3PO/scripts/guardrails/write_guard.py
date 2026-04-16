"""FileWriteGuard — Validates file writes against phase and path restrictions."""

from fnmatch import fnmatch

from constants import (
    TEST_FILE_PATTERNS,
    CODE_EXTENSIONS,
    PACKAGE_MANAGER_FILES,
)
from typing import Literal

from lib.state_store import StateStore
from lib.extractors import extract_md_sections
from config import Config


Decision = tuple[Literal["allow", "block"], str]

E2E_TEST_REPORT = ".claude/reports/E2E_TEST_REPORT.md"


def _is_e2e_report_path(file_path: str) -> bool:
    """Match any top-level E2E*_TEST_REPORT.md or the legacy .claude/reports path."""
    if not file_path:
        return False
    basename = file_path.rsplit("/", 1)[-1]
    if basename.startswith("E2E") and basename.endswith("_TEST_REPORT.md"):
        return True
    return file_path == E2E_TEST_REPORT or file_path.endswith(E2E_TEST_REPORT)


class FileWriteGuard:
    """Validate file write against phase and path restrictions."""

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.phase = state.current_phase
        self.file_path = hook_input.get("tool_input", {}).get("file_path", "")
        self.content = hook_input.get("tool_input", {}).get("content", "")

    # ── Test mode ─────────────────────────────────────────────────

    def _is_test_report(self) -> bool:
        return bool(self.state.get("test_mode")) and _is_e2e_report_path(self.file_path)

    def _is_state_file(self) -> bool:
        return self.state.get("test_mode") and self.file_path.endswith("state.jsonl")

    # ── Phase check ───────────────────────────────────────────────

    def _check_writable_phase(self) -> None:
        writable = self.config.code_write_phases + self.config.docs_write_phases
        if self.phase not in writable:
            raise ValueError(f"File write not allowed in phase: {self.phase}")

    # ── Plan phase ────────────────────────────────────────────────

    def _check_agent_completed(self, agent_name: str) -> None:
        agents = [a for a in self.state.agents if a.get("name") == agent_name]
        if not agents:
            raise ValueError(f"{agent_name} agent must be invoked first")
        if not all(a.get("status") == "completed" for a in agents):
            raise ValueError(f"{agent_name} agent must complete before writing")

    def _check_plan_path(self) -> None:
        allowed = [self.config.plan_file_path, self.config.contracts_file_path]
        if not any(
            self.file_path == p or self.file_path.endswith(p) for p in allowed if p
        ):
            raise ValueError(
                f"Writing '{self.file_path}' not allowed\nAllowed: {allowed}"
            )

    def _is_plan_file(self) -> bool:
        return self.file_path == self.config.plan_file_path or self.file_path.endswith(
            self.config.plan_file_path
        )

    def _is_contracts_file(self) -> bool:
        return self.config.contracts_file_path and (
            self.file_path == self.config.contracts_file_path
            or self.file_path.endswith(self.config.contracts_file_path)
        )

    def _check_plan_content(self) -> None:
        workflow_type = self.state.get("workflow_type", "build")
        if workflow_type == "implement":
            self._check_implement_plan_sections()
        else:
            self._check_build_plan_sections()

    def _check_build_plan_sections(self) -> None:
        required = self.config.build_plan_required_sections
        missing = [s for s in required if s not in self.content]
        if missing:
            raise ValueError(f"Plan missing required sections: {missing}")

        sections = extract_md_sections(self.content, 2)
        section_map = {name.strip(): body for name, body in sections}

        for section_name in self.config.build_plan_bullet_sections:
            body = section_map.get(section_name, "")
            if "### " in body:
                raise ValueError(
                    f"'{section_name}' must use bullet items (- item), not ### subsections. "
                    f"See the plan template for the correct format."
                )
            if not any(line.strip().startswith("- ") for line in body.splitlines()):
                raise ValueError(
                    f"'{section_name}' must have at least one bullet item (- item). "
                    f"See the plan template for the correct format."
                )

    def _check_implement_plan_sections(self) -> None:
        required = self.config.implement_plan_required_sections
        missing = [s for s in required if s not in self.content]
        if missing:
            raise ValueError(f"Plan missing required sections: {missing}")

    def _check_contracts_content(self) -> None:
        if "## Specifications" not in self.content:
            raise ValueError(
                "Contracts file missing required section: ## Specifications. "
                "See the contracts template for the correct format."
            )
        from lib.extractors import extract_table

        sections = extract_md_sections(self.content, 2)
        for name, body in sections:
            if name.strip() == "Specifications":
                table = extract_table(body)
                if len(table) < 2:
                    raise ValueError(
                        "## Specifications must have at least one contract in the table. "
                        "See the contracts template for the correct format."
                    )
                return
        raise ValueError("## Specifications section is empty.")

    def _validate_plan(self) -> None:
        self._check_agent_completed("Plan")
        self._check_plan_path()
        if self._is_plan_file():
            self._check_plan_content()
        if self._is_contracts_file():
            workflow_type = self.state.get("workflow_type", "build")
            if workflow_type == "build":
                self._check_contracts_content()

    # ── Other phases ──────────────────────────────────────────────

    def _check_package_manager_path(self) -> None:
        basename = self.file_path.rsplit("/", 1)[-1]
        if basename not in PACKAGE_MANAGER_FILES:
            raise ValueError(
                f"Writing '{self.file_path}' not allowed in install-deps"
                f"\nAllowed: {PACKAGE_MANAGER_FILES}"
            )

    def _check_contract_file(self) -> None:
        contract_files = self.state.get("contract_files", [])
        if contract_files:
            if self.file_path not in contract_files and not any(
                self.file_path.endswith(f) for f in contract_files
            ):
                raise ValueError(
                    f"Writing '{self.file_path}' not in contracts ## Specifications file list"
                    f"\nAllowed: {contract_files}"
                )
        else:
            self._check_code_path()

    def _check_test_path(self) -> None:
        basename = self.file_path.rsplit("/", 1)[-1]
        if not any(fnmatch(basename, p) for p in TEST_FILE_PATTERNS):
            raise ValueError(
                f"Writing '{self.file_path}' not allowed"
                f"\nAllowed patterns: {TEST_FILE_PATTERNS}"
            )

    def _check_code_path(self) -> None:
        if not any(self.file_path.endswith(ext) for ext in CODE_EXTENSIONS):
            raise ValueError(
                f"Writing '{self.file_path}' not allowed"
                f"\nAllowed extensions: {CODE_EXTENSIONS}"
            )

    def _check_implement_code_path(self) -> None:
        allowed = self.state.plan_files_to_modify
        if self.file_path not in allowed:
            raise ValueError(
                f"Writing '{self.file_path}' not in plan's ## Files to Create/Modify"
                f"\nAllowed: {allowed}"
            )

    def _check_report_path(self) -> None:
        expected = self.config.report_file_path
        if self.file_path != expected and not self.file_path.endswith(expected):
            raise ValueError(
                f"Writing '{self.file_path}' not allowed\nAllowed: {expected}"
            )

    def _validate_write_code(self) -> None:
        workflow_type = self.state.get("workflow_type", "build")
        if workflow_type == "implement":
            self._check_implement_code_path()
        else:
            self._check_code_path()

    # ── Phase dispatch ────────────────────────────────────────────

    def validate(self) -> Decision:
        """Returns ("allow", message) or ("block", reason)."""
        try:
            if self._is_test_report():
                return "allow", "E2E test report write allowed (test mode)"

            if self._is_state_file():
                return "allow", "State file write allowed (test mode)"

            self._check_writable_phase()

            if self.phase == "plan":
                self._validate_plan()
            elif self.phase == "install-deps":
                self._check_package_manager_path()
            elif self.phase == "define-contracts":
                self._check_contract_file()
            elif self.phase == "write-tests":
                self._check_test_path()
            elif self.phase == "write-code":
                self._validate_write_code()
            elif self.phase == "write-report":
                self._check_report_path()

            return "allow", f"File write allowed in phase: {self.phase}"
        except ValueError as e:
            return "block", str(e)
