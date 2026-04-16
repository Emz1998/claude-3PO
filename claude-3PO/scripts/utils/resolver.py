"""Resolver — Evaluates state after each tool call and resolves phase completion.

After a recorder writes raw data to state, the resolver checks completion
conditions for the current phase and auto-starts the next phase if needed.
"""

from typing import Literal

from lib.state_store import StateStore
from config import Config


class Resolver:
    """Resolve phase completion based on current state."""

    def __init__(self, config: Config, state: StateStore):
        self.config = config
        self.state = state
        self.phase = state.current_phase

    # ══════════════════════════════════════════════════════════════
    # Phase resolvers (reviews, agents)
    # ══════════════════════════════════════════════════════════════

    # ── Score-based reviews ───────────────────────────────────────

    def _is_revision_needed(
        self,
        file_type: Literal["plan", "report", "tests", "code"],
        confidence: int,
        quality: int,
    ) -> bool:
        conf_threshold = self.config.get_score_threshold(file_type, "confidence_score")
        qual_threshold = self.config.get_score_threshold(file_type, "quality")

        if confidence < conf_threshold and quality < qual_threshold:
            raise ValueError(f"Scores are below the threshold for {file_type}")
        if confidence < conf_threshold:
            raise ValueError(f"Confidence score is below the threshold for {file_type}")
        if quality < qual_threshold:
            raise ValueError(f"Quality score is below the threshold for {file_type}")
        return True

    def _get_pending_scores(self, last_getter: str) -> tuple[int, int] | None:
        """Get scores from the latest review if it hasn't been resolved yet."""
        last = getattr(self.state, last_getter)
        if not last or last.get("status"):
            return None
        scores = last.get("scores", {})
        confidence = scores.get("confidence_score", 0)
        quality = scores.get("quality_score", 0)
        if confidence == 0 and quality == 0:
            return None
        return confidence, quality

    def _mark_review_failed(self, file_type: str, status_setter: str) -> None:
        getattr(self.state, status_setter)("Fail")
        if file_type == "plan":
            self.state.set_plan_revised(False)

    def _mark_review_passed(self, status_setter: str, phase_name: str) -> None:
        getattr(self.state, status_setter)("Pass")
        self.state.set_phase_completed(phase_name)

    def _resolve_score_review(
        self,
        file_type: Literal["plan", "code"],
        last_getter: str,
        status_setter: str,
        phase_name: str,
    ) -> None:
        pending = self._get_pending_scores(last_getter)
        if pending is None:
            return

        confidence, quality = pending
        try:
            self._is_revision_needed(file_type, confidence, quality)
        except ValueError:
            self._mark_review_failed(file_type, status_setter)
            return

        self._mark_review_passed(status_setter, phase_name)

    def _resolve_plan_review(self) -> None:
        self._resolve_score_review(
            "plan", "last_plan_review", "set_last_plan_review_status", "plan-review"
        )

    def _resolve_code_review(self) -> None:
        self._resolve_score_review(
            "code", "last_code_review", "set_last_code_review_status", "code-review"
        )

    # ── Verdict-based reviews ─────────────────────────────────────

    def _resolve_test_review(self) -> None:
        last = self.state.last_test_review
        if not last:
            return
        verdict = last.get("verdict")
        if verdict == "Pass":
            phase = self.phase
            if phase in ("test-review", "tests-review"):
                self.state.set_phase_completed(phase)
            else:
                self.state.set_phase_completed("test-review")

    def _resolve_quality_check(self) -> None:
        if self.state.quality_check_result == "Pass":
            self.state.set_phase_completed("quality-check")

    def _resolve_validate(self) -> None:
        if self.state.quality_check_result == "Pass":
            self.state.set_phase_completed("validate")

    # ── Agent-based phases ────────────────────────────────────────

    def _resolve_agent_phase(self, phase_name: str) -> None:
        agent_name = self.config.get_required_agent(phase_name)
        if not agent_name:
            return
        agents = [a for a in self.state.agents if a.get("name") == agent_name]
        if agents and all(a.get("status") == "completed" for a in agents):
            self.state.set_phase_completed(phase_name)

    def _resolve_explore(self) -> None:
        self._resolve_agent_phase("explore")

    def _resolve_research(self) -> None:
        self._resolve_agent_phase("research")

    # ══════════════════════════════════════════════════════════════
    # Tool resolvers (file writes, bash, tasks)
    # ══════════════════════════════════════════════════════════════

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

    # ── Helpers ───────────────────────────────────────────────────

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

    # ══════════════════════════════════════════════════════════════
    # Auto-start & workflow completion
    # ══════════════════════════════════════════════════════════════

    def _is_phase_ready_to_advance(self, skip_checkpoint: bool) -> bool:
        phase = self.state.current_phase
        if not phase or self.state.get_phase_status(phase) != "completed":
            return False
        if phase == "plan-review" and not skip_checkpoint:
            return False
        return True

    def _get_next_auto_phase(self) -> str | None:
        phase = self.state.current_phase
        workflow_type = self.state.get("workflow_type", "build")
        phases = self.config.get_phases(workflow_type) or self.config.main_phases

        if phase not in phases:
            return None

        idx = phases.index(phase)
        if idx + 1 >= len(phases):
            return None

        next_phase = phases[idx + 1]
        if not self.config.is_auto_phase(next_phase):
            return None

        return next_phase

    def _skip_tdd_phases(self, next_phase: str) -> str | None:
        if self.state.get("tdd", False) or next_phase != "write-tests":
            return next_phase

        workflow_type = self.state.get("workflow_type", "build")
        phases = self.config.get_phases(workflow_type) or self.config.main_phases
        phase = self.state.current_phase
        skip_idx = phases.index(phase) + 1

        while skip_idx < len(phases) and phases[skip_idx] in ("write-tests", "test-review", "tests-review"):
            skip_idx += 1

        if skip_idx < len(phases) and self.config.is_auto_phase(phases[skip_idx]):
            return phases[skip_idx]
        return None

    def auto_start_next(self, skip_checkpoint: bool = False) -> None:
        if not self._is_phase_ready_to_advance(skip_checkpoint):
            return

        next_phase = self._get_next_auto_phase()
        if next_phase is None:
            return

        next_phase = self._skip_tdd_phases(next_phase)
        if next_phase is None:
            return

        self.state.add_phase(next_phase)

    def _check_workflow_complete(self) -> None:
        if self.state.get("status") == "completed":
            return

        workflow_type = self.state.get("workflow_type", "build")
        phases = self.config.get_phases(workflow_type) or self.config.main_phases
        skip = self.state.get("skip", [])
        tdd = self.state.get("tdd", False)

        required = [p for p in phases if p not in skip]
        if not tdd:
            required = [
                p
                for p in required
                if p not in ("write-tests", "test-review", "tests-review")
            ]

        completed = {p["name"] for p in self.state.phases if p["status"] == "completed"}
        if all(p in completed for p in required):
            self.state.set("status", "completed")
            self.state.set("workflow_active", False)

    # ══════════════════════════════════════════════════════════════
    # Main dispatch
    # ══════════════════════════════════════════════════════════════

    _PHASE_RESOLVER_MAP: dict[str, str] = {
        "explore": "_resolve_explore",
        "research": "_resolve_research",
        "plan-review": "_resolve_plan_review",
        "test-review": "_resolve_test_review",
        "tests-review": "_resolve_test_review",
        "code-review": "_resolve_code_review",
        "quality-check": "_resolve_quality_check",
        "validate": "_resolve_validate",
    }

    _TOOL_RESOLVER_MAP: dict[str, str] = {
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
        """Main resolver — dispatch phase + tool resolvers, then auto-advance."""
        # Phase-specific (reviews, agents)
        method_name = self._PHASE_RESOLVER_MAP.get(self.phase)
        if method_name:
            getattr(self, method_name)()

        # Tool-specific (file writes, bash output, tasks)
        method_name = self._TOOL_RESOLVER_MAP.get(self.phase)
        if method_name:
            getattr(self, method_name)()

        # Parallel case: resolve explore if it's still in_progress while research is current
        if (
            self.phase == "research"
            and self.state.get_phase_status("explore") == "in_progress"
        ):
            self._resolve_explore()

        self.auto_start_next()
        self._check_workflow_complete()


# ══════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════


def resolve(config: Config, state: StateStore) -> None:
    Resolver(config, state).resolve()
