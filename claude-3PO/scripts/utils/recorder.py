"""Recorder — Records state changes after successful tool use."""

import json
import re
from pathlib import Path

from constants import TEST_RUN_PATTERNS, INSTALL_COMMANDS
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
from lib.parallel_check import is_parallel_explore_research
from lib.scoring import scores_valid, verdict_valid
from lib.state_store import StateStore
from lib.paths import basenames
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

    def _is_session_file(self, file_path: str) -> bool:
        """Check if file is a code or test file tracked in the current session."""
        code_files = self.state.code_files.get("file_paths", [])
        test_files = self.state.tests.get("file_paths", [])
        all_files = basenames(code_files + test_files)
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

    _SPECS_DOC_PHASES: dict[str, str] = {"vision": "product_vision", "decision": "decisions"}

    def record_write(self, phase: str, file_path: str, is_plan_file: bool) -> None:
        if phase == "plan":
            self._record_plan_write(file_path, is_plan_file)
        elif phase == "define-contracts":
            self.state.add_contract_code_file(file_path)
            self.state.set_contracts_written(True)
        elif phase == "write-tests":
            self.state.add_test_file(file_path)
        elif phase == "write-code":
            self.state.add_code_file(file_path)
        elif phase == "write-report":
            self.state.set_report_written(True)
        elif phase in self._SPECS_DOC_PHASES:
            self._record_specs_doc(self._SPECS_DOC_PHASES[phase], file_path)

    def _record_plan_write(self, file_path: str, is_plan_file: bool) -> None:
        if is_plan_file:
            self.state.set_plan_file_path(file_path)
            self.state.set_plan_written(True)

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
            to_revise_basenames = basenames(self.state.code_tests_to_revise)
            if basename in to_revise_basenames:
                self.state.add_code_test_revised(file_path)
            elif self._is_session_file(file_path):
                self.state.add_file_revised(file_path)

    # ── Agent report ──────────────────────────────────────────────

    def record_scores(self, phase: str, content: str) -> None:
        if phase in ("plan-review", "code-review"):
            _, extracted = scores_valid(content, extract_scores)
            if phase == "plan-review":
                self.state.add_plan_review(extracted)
            else:
                self.state.add_code_review(extracted)

    def record_verdict(self, phase: str, content: str) -> None:
        if phase == "test-review":
            _, verdict = verdict_valid(content, extract_verdict)
            self.state.add_test_review(verdict)

        if phase in ("quality-check", "validate"):
            _, verdict = verdict_valid(content, extract_verdict)
            self.state.set_quality_check_result(verdict)

    def record_revision_files(
        self, phase: str, files: list[str], tests: list[str]
    ) -> None:
        if phase == "code-review" and files:
            self.state.set_files_to_revise(files)
            self.state.set_code_tests_to_revise(tests)
        elif phase == "test-review" and files:
            self.state.set_test_files_to_revise(files)

    # ── Specs report side-effects (moved from AgentReportGuard) ───

    _SPECS_AGENT_BY_PHASE = {"architect": "Architect", "backlog": "ProductOwner"}

    def write_specs_doc(self, phase: str, content: str, config: Config) -> None:
        """Write architect/backlog content to disk and record paths in state."""
        if phase == "architect":
            self._write_architecture(content, config)
        elif phase == "backlog":
            self._write_backlog(content, config)

    def _write_architecture(self, content: str, config: Config) -> None:
        from utils.specs_writer import write_doc

        path = config.architecture_file_path
        write_doc(content, path)
        self.state.set_doc_written("architecture", True)
        self.state.set_doc_path("architecture", path)

    def _write_backlog(self, content: str, config: Config) -> None:
        from utils.specs_writer import write_backlog

        md_path = config.backlog_md_file_path
        json_path = config.backlog_json_file_path
        write_backlog(content, md_path, json_path)
        self.state.set_doc_written("backlog", True)
        self.state.set_doc_md_path("backlog", md_path)
        self.state.set_doc_json_path("backlog", json_path)

    def mark_specs_agent_failed(self, phase: str) -> None:
        agent_name = self._SPECS_AGENT_BY_PHASE.get(phase)
        if agent_name:
            self.state.mark_last_agent_failed(agent_name)

    # ── TaskCreated side-effects (moved from TaskCreatedGuard) ────

    def record_created_task(self, matched_subject: str) -> None:
        self.state.add_created_task(matched_subject)

    def record_subtask(self, parent_id: str, payload: dict) -> None:
        self.state.add_subtask(parent_id, payload)

    # ── Skill side-effects (moved from PhaseGuard) ────────────────

    def apply_phase_skill(self, skill: str, current: str, status: str) -> None:
        """Mutate state for the meta-skills /continue, /plan-approved, /revise-plan."""
        handler = self._PHASE_SKILL_HANDLERS.get(skill)
        if handler is not None:
            handler(self, current, status)

    def _apply_continue(self, current: str, status: str) -> None:
        if status == "in_progress":
            self.state.set_phase_completed(current)

    def _apply_plan_approved(self, current: str, status: str) -> None:
        if status == "in_progress":
            self.state.set_phase_completed("plan-review")

    def _apply_revise_plan(self, current: str, status: str) -> None:
        def _reopen(d: dict) -> None:
            for p in d.get("phases", []):
                if p["name"] == "plan-review":
                    p["status"] = "in_progress"
                    break
            plan = d.setdefault("plan", {})
            plan["revised"] = False
            plan["reviews"] = []

        self.state.update(_reopen)

    _PHASE_SKILL_HANDLERS: dict = {
        "continue": _apply_continue,
        "plan-approved": _apply_plan_approved,
        "revise-plan": _apply_revise_plan,
    }

    # ── Dispatch ──────────────────────────────────────────────────

    def _dispatch_edit(self, hook_input: dict, config: Config, phase: str) -> None:
        self.record_edit(phase, hook_input.get("tool_input", {}).get("file_path", ""))

    def _dispatch_bash(self, hook_input: dict, config: Config, phase: str) -> None:
        self._record_bash(
            hook_input.get("tool_input", {}), hook_input.get("tool_result", ""), phase
        )

    def _dispatch_skill(self, hook_input: dict, config: Config, phase: str) -> None:
        self._record_skill(hook_input.get("tool_input", {}), phase)

    def _dispatch_write(self, hook_input: dict, config: Config, phase: str) -> None:
        self._record_file_write(hook_input.get("tool_input", {}), config, phase)

    TOOL_RECORDERS: dict = {
        "Skill": _dispatch_skill,
        "Write": _dispatch_write,
        "Edit": _dispatch_edit,
        "Bash": _dispatch_bash,
    }

    def record(self, hook_input: dict, config: Config) -> None:
        """Record state changes for a completed tool use. Raises ValueError for parse failures."""
        handler = self.TOOL_RECORDERS.get(hook_input.get("tool_name", ""))
        if handler is None:
            return
        handler(self, hook_input, config, self.state.current_phase)

    def _record_skill(self, tool_input: dict, phase: str) -> None:
        skill = extract_skill_name({"tool_input": tool_input})
        current = self.state.current_phase
        parallel = is_parallel_explore_research(
            current, self.state.get_phase_status(current) if current else None, skill
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
        if file_path and self._is_contracts_write(file_path, config):
            self.record_contracts_file(file_path)

    @staticmethod
    def _is_contracts_write(file_path: str, config: Config) -> bool:
        return bool(config.contracts_file_path) and file_path.endswith(
            config.contracts_file_path
        )

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
