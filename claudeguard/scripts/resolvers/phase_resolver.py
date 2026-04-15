"""PhaseResolver — Evaluates state after each tool call and resolves phase completion.

After a recorder writes raw data to state, the resolver checks completion
conditions for the current phase and auto-starts the next phase if needed.
"""

from typing import Literal

from utils.state_store import StateStore
from config import Config


class PhaseResolver:
    """Resolve phase completion based on current state."""

    def __init__(self, config: Config, state: StateStore):
        self.config = config
        self.state = state
        self.phase = state.current_phase

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

    def _resolve_score_review(
        self,
        file_type: Literal["plan", "code"],
        last_getter: str,
        status_setter: str,
        phase_name: str,
    ) -> None:
        last = getattr(self.state, last_getter)
        if not last or last.get("status"):
            return

        scores = last.get("scores", {})
        confidence = scores.get("confidence_score", 0)
        quality = scores.get("quality_score", 0)
        if confidence == 0 and quality == 0:
            return

        try:
            self._is_revision_needed(file_type, confidence, quality)
        except ValueError:
            getattr(self.state, status_setter)("Fail")
            if file_type == "plan":
                self.state.set_plan_revised(False)
            return

        getattr(self.state, status_setter)("Pass")
        self.state.set_phase_completed(phase_name)

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


    # ── Auto-start next phase ─────────────────────────────────────

    def _is_phase_ready_to_advance(self, skip_checkpoint: bool) -> bool:
        phase = self.state.current_phase
        if not phase or self.state.get_phase_status(phase) != "completed":
            return False
        if phase == "plan-review" and not skip_checkpoint:
            return False
        return True

    def _get_next_auto_phase(self) -> str | None:
        """Return the next auto-phase after current, or None."""
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
        """If TDD is off and next_phase is write-tests, skip to the next auto-phase after test phases."""
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
        """If the current phase just completed and the next is an auto-phase, start it."""
        if not self._is_phase_ready_to_advance(skip_checkpoint):
            return

        next_phase = self._get_next_auto_phase()
        if next_phase is None:
            return

        next_phase = self._skip_tdd_phases(next_phase)
        if next_phase is None:
            return

        self.state.add_phase(next_phase)

    # ── Workflow completion ────────────────────────────────────────

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

    # ── Main dispatch ─────────────────────────────────────────────

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

    def resolve(self) -> None:
        """Main resolver — dispatch phase + tool resolvers, then auto-advance."""
        from .tool_resolver import ToolResolver

        # Phase-specific (reviews, agents)
        method_name = self._PHASE_RESOLVER_MAP.get(self.phase)
        if method_name:
            getattr(self, method_name)()

        # Tool-specific (file writes, bash output, tasks)
        ToolResolver(self.config, self.state).resolve()

        # Parallel case: resolve explore if it's still in_progress while research is current
        if (
            self.phase == "research"
            and self.state.get_phase_status("explore") == "in_progress"
        ):
            self._resolve_explore()

        self.auto_start_next()
        self._check_workflow_complete()
