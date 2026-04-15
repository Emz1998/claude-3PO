"""ToolResolver — Resolves phase completion based on tool output (Write, Bash).

These resolvers check if a phase's completion criteria are met after
a tool records its result (file written, command executed, etc.).
"""

from utils.state_store import StateStore
from config import Config


class ToolResolver:
    """Resolve phase completion based on tool results."""

    def __init__(self, config: Config, state: StateStore):
        self.config = config
        self.state = state
        self.phase = state.current_phase

    # ── Plan ──────────────────────────────────────────────────────

    def _resolve_plan(self) -> None:
        agent_name = self.config.get_required_agent("plan")
        if agent_name:
            agents = [a for a in self.state.agents if a.get("name") == agent_name]
            if not agents or not all(a.get("status") == "completed" for a in agents):
                return
        plan = self.state.plan
        if plan.get("written") and plan.get("file_path"):
            self.state.set_phase_completed("plan")

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _basenames(paths: list[str]) -> set:
        return {p.rsplit("/", 1)[-1] for p in paths}

    # ── Write phases ──────────────────────────────────────────────

    def _resolve_write_code(self) -> None:
        to_write = self._basenames(self.state.code_files_to_write)
        written = self._basenames(self.state.code_files.get("file_paths", []))
        if to_write and not (to_write - written):
            self.state.set_phase_completed("write-code")

    def _resolve_write_tests(self) -> None:
        tests = self.state.tests
        file_paths = tests.get("file_paths", [])
        if file_paths and tests.get("executed"):
            self.state.set_phase_completed("write-tests")

    def _resolve_report(self) -> None:
        if self.state.report_written:
            self.state.set_phase_completed("write-report")

    # ── Install / contracts ───────────────────────────────────────

    def _resolve_install_deps(self) -> None:
        if self.state.dependencies.get("installed"):
            self.state.set_phase_completed("install-deps")

    @staticmethod
    def _find_contract_names_in_files(
        names: list[str], code_files: list[str]
    ) -> set[str]:
        from pathlib import Path

        found = set()
        for fp in code_files:
            path = Path(fp)
            if path.exists():
                content = path.read_text()
                for name in names:
                    if name in content:
                        found.add(name)
        return found

    def _are_contracts_written(self) -> bool:
        return bool(self.state.contracts.get("written"))

    def _are_contracts_validated(self) -> bool:
        return bool(self.state.contracts.get("validated"))

    def _validate_and_complete_contracts(self) -> None:
        contracts = self.state.contracts
        names = contracts.get("names", [])
        code_files = contracts.get("code_files", [])
        if not names or not code_files:
            return

        found = self._find_contract_names_in_files(names, code_files)
        if found >= set(names):
            self.state.set_contracts_validated(True)
            self.state.set_phase_completed("define-contracts")

    def _resolve_define_contracts(self) -> None:
        if not self._are_contracts_written():
            return
        if self._are_contracts_validated():
            self.state.set_phase_completed("define-contracts")
            return
        self._validate_and_complete_contracts()

    # ── Tasks ─────────────────────────────────────────────────────

    def _all_tasks_created(self) -> bool:
        planned = set(self.state.tasks)
        created = set(self.state.created_tasks)
        return bool(planned) and not (planned - created)

    def _all_project_tasks_have_subtasks(self) -> bool:
        ptasks = self.state.project_tasks
        if not ptasks:
            return False
        return all(len(pt.get("subtasks", [])) >= 1 for pt in ptasks)

    def _resolve_create_tasks(self) -> None:
        workflow_type = self.state.get("workflow_type", "build")
        if workflow_type == "implement":
            if self._all_project_tasks_have_subtasks():
                self.state.set_phase_completed("create-tasks")
        else:
            if self._all_tasks_created():
                self.state.set_phase_completed("create-tasks")

    # ── Delivery ──────────────────────────────────────────────────

    def _resolve_pr_create(self) -> None:
        if self.state.pr_status == "created":
            self.state.set_phase_completed("pr-create")

    def _resolve_ci_check(self) -> None:
        if self.state.ci_status == "passed":
            self.state.set_phase_completed("ci-check")

    # ── Dispatch ──────────────────────────────────────────────────

    _RESOLVER_MAP: dict[str, str] = {
        "plan": "_resolve_plan",
        "install-deps": "_resolve_install_deps",
        "define-contracts": "_resolve_define_contracts",
        "create-tasks": "_resolve_create_tasks",
        "write-tests": "_resolve_write_tests",
        "write-code": "_resolve_write_code",
        "pr-create": "_resolve_pr_create",
        "ci-check": "_resolve_ci_check",
        "write-report": "_resolve_report",
    }

    def resolve(self) -> None:
        """Resolve tool-based phase completion for the current phase."""
        method_name = self._RESOLVER_MAP.get(self.phase)
        if method_name:
            getattr(self, method_name)()
