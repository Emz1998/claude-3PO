"""Recorder — Records state changes after successful tool use."""

import json
import re
from pathlib import Path

from constants import TEST_RUN_PATTERNS, INSTALL_COMMANDS
from guardrails.agent_report_guard import AgentReportGuard
from lib.extractors import (
    extract_skill_name,
    extract_scores,
    extract_verdict,
    extract_plan_dependencies,
    extract_plan_tasks,
    extract_plan_files_to_modify,
    extract_contract_names,
    extract_contract_files,
)
from lib.state_store import StateStore
from config import Config


_NO_TRANSITION_SKILLS = (
    "continue",
    "revise-plan",
    "plan-approved",
    "reset-plan-review",
)


class Recorder:
    """Records state changes after guards allow a tool use."""

    def __init__(self, state: StateStore):
        self.state = state

    @staticmethod
    def _basenames(paths: list[str]) -> set:
        return {p.rsplit("/", 1)[-1] for p in paths}

    def _is_session_file(self, file_path: str) -> bool:
        """Check if file is a code or test file tracked in the current session."""
        code_files = self.state.code_files.get("file_paths", [])
        test_files = self.state.tests.get("file_paths", [])
        all_files = self._basenames(code_files + test_files)
        basename = file_path.rsplit("/", 1)[-1]
        return basename in all_files

    # ── Phase transition ──────────────────────────────────────────

    def record_phase_transition(
        self, current: str, next_phase: str, parallel: bool = False
    ) -> None:
        if next_phase in _NO_TRANSITION_SKILLS:
            return
        if current and not parallel:
            self.state.set_phase_completed(current)
        self.state.add_phase(next_phase)

    # ── Command ───────────────────────────────────────────────────

    def record_test_execution(self, phase: str, command: str) -> None:
        if phase in ("write-tests", "test-review"):
            if any(re.search(p, command) for p in TEST_RUN_PATTERNS):
                self.state.set_tests_executed(True)

    def record_pr_create(self, output: str) -> None:
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse PR create output as JSON: {output}")
        number = data.get("number")
        if number is None:
            raise ValueError("PR create output missing 'number' field")
        self.state.set_pr_number(number)
        self.state.set_pr_status("created")

    def record_ci_check(self, output: str) -> None:
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse CI check output as JSON: {output}")
        results = data if isinstance(data, list) else data.get("checks", [])
        self.state.set_ci_results(results)
        if any(r.get("conclusion") == "FAILURE" for r in results):
            self.state.set_ci_status("failed")
        elif all(r.get("conclusion") == "SUCCESS" for r in results):
            self.state.set_ci_status("passed")
        else:
            self.state.set_ci_status("pending")

    def record_deps_installed(self, phase: str, command: str) -> None:
        if phase == "install-deps" and any(
            command.startswith(cmd) for cmd in INSTALL_COMMANDS
        ):
            self.state.set_dependencies_installed()

    # ── File write ────────────────────────────────────────────────

    def record_write(self, phase: str, file_path: str, is_plan_file: bool) -> None:
        if phase == "plan":
            if is_plan_file:
                self.state.set_plan_file_path(file_path)
                self.state.set_plan_written(True)
        elif phase == "define-contracts":
            self.state.add_contract_code_file(file_path)
            self.state.set_contracts_written(True)
        elif phase == "write-tests":
            self.state.add_test_file(file_path)
        elif phase == "write-code":
            self.state.add_code_file(file_path)
        elif phase == "write-report":
            self.state.set_report_written(True)
        elif phase == "vision":
            self._record_specs_doc("product_vision", file_path)
        elif phase == "decision":
            self._record_specs_doc("decisions", file_path)

    def _record_specs_doc(self, doc_key: str, file_path: str) -> None:
        self.state.set_doc_written(doc_key, True)
        self.state.set_doc_path(doc_key, file_path)

    def record_plan_metadata(self, file_path: str) -> None:
        from lib.injector import inject_plan_metadata
        inject_plan_metadata(file_path, self.state)

    def record_plan_sections(self, file_path: str) -> None:
        """Auto-parse Dependencies, Tasks, and Files to Modify from plan."""
        path = Path(file_path)
        if not path.exists():
            return

        content = path.read_text()
        self.state.set_dependencies_packages(extract_plan_dependencies(content))
        self.state.set_tasks(extract_plan_tasks(content))

        for f in extract_plan_files_to_modify(content):
            self.state.add_code_file_to_write(f)

    def record_contracts_file(self, file_path: str) -> None:
        """Auto-parse contract names and file paths from contracts.md."""
        path = Path(file_path)
        if not path.exists():
            return

        content = path.read_text()
        self.state.set_contracts_file_path(file_path)
        self.state.set_contracts_names(extract_contract_names(content))

        files = extract_contract_files(content)
        if files:
            self.state.set("contract_files", files)

    # ── File edit ─────────────────────────────────────────────────

    def record_edit(self, phase: str, file_path: str) -> None:
        if phase == "plan-review":
            self.state.set_plan_revised(True)
        elif phase == "test-review" and file_path:
            self.state.add_test_file_revised(file_path)
        elif phase == "code-review" and file_path:
            basename = file_path.rsplit("/", 1)[-1]
            to_revise_basenames = self._basenames(self.state.code_tests_to_revise)
            if basename in to_revise_basenames:
                self.state.add_code_test_revised(file_path)
            elif self._is_session_file(file_path):
                self.state.add_file_revised(file_path)

    # ── Agent report ──────────────────────────────────────────────

    def record_scores(self, phase: str, content: str) -> None:
        if phase in ("plan-review", "code-review"):
            _, extracted = AgentReportGuard.scores_valid(content, extract_scores)
            if phase == "plan-review":
                self.state.add_plan_review(extracted)
            else:
                self.state.add_code_review(extracted)

    def record_verdict(self, phase: str, content: str) -> None:
        if phase == "test-review":
            _, verdict = AgentReportGuard.verdict_valid(content, extract_verdict)
            self.state.add_test_review(verdict)

        if phase in ("quality-check", "validate"):
            _, verdict = AgentReportGuard.verdict_valid(content, extract_verdict)
            self.state.set_quality_check_result(verdict)

    def record_revision_files(
        self, phase: str, files: list[str], tests: list[str]
    ) -> None:
        if phase == "code-review" and files:
            self.state.set_files_to_revise(files)
            self.state.set_code_tests_to_revise(tests)
        elif phase == "test-review" and files:
            self.state.set_test_files_to_revise(files)

    # ── Dispatch ──────────────────────────────────────────────────

    def record(self, hook_input: dict, config: Config) -> None:
        """Record state changes for a completed tool use. Raises ValueError for parse failures."""
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})
        phase = self.state.current_phase

        if tool_name == "Skill":
            self._record_skill(tool_input, phase)
        elif tool_name == "Write":
            self._record_file_write(tool_input, config, phase)
        elif tool_name == "Edit":
            self.record_edit(phase, tool_input.get("file_path", ""))
        elif tool_name == "Bash":
            self._record_bash(tool_input, hook_input.get("tool_result", ""), phase)

    def _record_skill(self, tool_input: dict, phase: str) -> None:
        skill = extract_skill_name({"tool_input": tool_input})
        current = self.state.current_phase
        parallel = (
            current == "explore"
            and self.state.get_phase_status("explore") == "in_progress"
            and skill == "research"
        )
        self.record_phase_transition(current, skill, parallel=parallel)

    def _record_file_write(self, tool_input: dict, config: Config, phase: str) -> None:
        file_path = tool_input.get("file_path", "")
        is_plan = bool(file_path and file_path.endswith(config.plan_file_path))

        if self._is_specs_phase_mismatch(phase, file_path, config):
            return

        record_path = self._canonicalize_specs_path(phase, file_path, config)
        self.record_write(phase, record_path, is_plan)

        if is_plan:
            self.record_plan_metadata(file_path)
            self.record_plan_sections(file_path)
        if (
            file_path
            and config.contracts_file_path
            and file_path.endswith(config.contracts_file_path)
        ):
            self.record_contracts_file(file_path)

    @staticmethod
    def _canonicalize_specs_path(phase: str, file_path: str, config: Config) -> str:
        """Store vision/decision docs under their config-relative path so all
        specs doc entries in state.jsonl use the same format (matches architecture/backlog)."""
        canonical = {
            "vision": config.product_vision_file_path,
            "decision": config.decisions_file_path,
        }.get(phase)
        return canonical if canonical else file_path

    @staticmethod
    def _is_specs_phase_mismatch(phase: str, file_path: str, config: Config) -> bool:
        """True when the write path doesn't match the specs phase's canonical doc path."""
        expected = {
            "vision": config.product_vision_file_path,
            "decision": config.decisions_file_path,
        }.get(phase)
        if not expected:
            return False
        return not (file_path and file_path.endswith(expected))

    def _record_bash(self, tool_input: dict, tool_output: str, phase: str) -> None:
        command = tool_input.get("command", "")

        self.record_test_execution(phase, command)
        self.record_deps_installed(phase, command)

        if phase == "pr-create" and command.startswith("gh pr create"):
            self.record_pr_create(tool_output)
        if phase == "ci-check" and command.startswith("gh pr checks"):
            self.record_ci_check(tool_output)
