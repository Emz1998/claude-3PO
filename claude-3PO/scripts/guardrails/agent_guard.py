"""AgentGuard — Validates agent invocation against phase and count restrictions."""

from typing import Literal

from lib.state_store import StateStore
from lib.extractors import extract_agent_name
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class AgentGuard:
    """Validate agent invocation against phase and count restrictions."""

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        self.config = config
        self.state = state
        self.phase = state.current_phase
        self.next_agent = extract_agent_name(hook_input)

    # ── Parallel explore+research ─────────────────────────────────

    def _is_parallel_research_allowed(self) -> bool:
        explore = self.state.get_agent("Explore")
        return (
            explore is not None
            and explore.get("status") == "in_progress"
            and self.next_agent == "Research"
        )

    def _resolve_parallel_phase(self) -> None:
        """When research is running but user wants more Explore agents, use explore phase."""
        if (
            self.next_agent == "Explore"
            and self.phase == "research"
            and self.state.get_phase_status("explore") is not None
        ):
            self.phase = "explore"

    # ── Checks ────────────────────────────────────────────────────

    @property
    def _phase_label(self) -> str:
        return self.phase or "(no phase active — workflow not started)"

    def _check_expected_agent(self) -> None:
        expected = self.config.get_required_agent(self.phase)
        if not expected:
            raise ValueError(f"No agent allowed in phase: {self._phase_label}")
        if self.next_agent != expected:
            raise ValueError(
                f"Agent '{self.next_agent}' not allowed in phase: {self._phase_label}"
                f"\nExpected: {expected}"
            )

    def _check_agent_count(self) -> None:
        max_allowed = self.config.get_agent_max_count(self.next_agent)
        actual = self.state.count_agents(self.next_agent)
        if actual >= max_allowed:
            raise ValueError(
                f"Agent '{self.next_agent}' at max ({max_allowed}) in phase: {self.phase}"
            )

    def _check_plan_revision_done(self) -> None:
        if self.state.plan_revised is False:
            raise ValueError("Plan must be revised before re-invoking PlanReview")

    @staticmethod
    def _basenames(paths: list[str]) -> set:
        return {p.rsplit("/", 1)[-1] for p in paths}

    def _all_revised(self, to_revise: list[str], revised: list[str]) -> bool:
        return bool(to_revise) and not (
            self._basenames(to_revise) - self._basenames(revised)
        )

    def _check_test_revision_done(self) -> None:
        last = self.state.last_test_review
        if last and last.get("verdict") == "Fail":
            if not self._all_revised(
                self.state.test_files_to_revise, self.state.test_files_revised
            ):
                raise ValueError(
                    "All test files must be revised before re-invoking TestReviewer"
                    f"\nFiles to revise: {self.state.test_files_to_revise}"
                    f"\nFiles revised: {self.state.test_files_revised}"
                )

    def _check_code_revision_done(self) -> None:
        last = self.state.last_code_review
        if last and last.get("status") == "Fail":
            if not self._all_revised(
                self.state.files_to_revise, self.state.files_revised
            ):
                raise ValueError(
                    "All files must be revised before re-invoking CodeReviewer"
                    f"\nFiles to revise: {self.state.files_to_revise}"
                    f"\nFiles revised: {self.state.files_revised}"
                )

    def _check_revision_done(self) -> None:
        if self.phase == "plan-review" and self.next_agent == "PlanReview":
            self._check_plan_revision_done()
        if (
            self.phase in ("test-review", "tests-review")
            and self.next_agent == "TestReviewer"
        ):
            self._check_test_revision_done()
        if self.phase == "code-review" and self.next_agent == "CodeReviewer":
            self._check_code_revision_done()

    # ── Validate ──────────────────────────────────────────────────

    def validate(self) -> Decision:
        """Returns ("allow", message) or ("block", reason)."""
        try:
            if self.phase == "explore" and self._is_parallel_research_allowed():
                return "allow", "Running Research in parallel with Explore"

            self._resolve_parallel_phase()
            self._check_expected_agent()
            self._check_agent_count()
            self._check_revision_done()

            return "allow", f"{self.next_agent} agent allowed in phase: {self.phase}"
        except ValueError as e:
            return "block", str(e)
