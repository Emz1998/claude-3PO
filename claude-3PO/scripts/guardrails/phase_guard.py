"""PhaseGuard — Validates phase transitions (skill invocations)."""

from typing import Literal

from lib.state_store import StateStore
from lib.extractors import extract_skill_name
from config import Config
from utils.resolver import Resolver


Decision = tuple[Literal["allow", "block"], str]

REVIEW_PHASES = {
    "plan-review",
    "test-review",
    "tests-review",
    "code-review",
    "quality-check",
    "validate",
}


class PhaseGuard:
    """Validate phase transition (skill invocation)."""

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.current = state.current_phase
        self.status = state.get_phase_status(self.current)
        self.next_phase = extract_skill_name(hook_input)
        self.phases = self._get_workflow_phases()

    def _get_workflow_phases(self) -> list[str]:
        workflow_type = self.state.get("workflow_type", "build")
        phases = self.config.get_phases(workflow_type)
        return phases if phases else self.config.main_phases

    # ── Order validation ──────────────────────────────────────────

    def _check_item_in_order(self, item: str, order: list[str], label: str) -> None:
        if item not in order:
            raise ValueError(f"Invalid {label} '{item}'")

    def _validate_order(
        self, prev: str | None, next_item: str, order: list[str]
    ) -> str:
        """Validate transition and return success message."""
        self._check_item_in_order(next_item, order, "next item")

        if prev is None:
            if next_item != order[0]:
                raise ValueError(f"Must start with '{order[0]}', not '{next_item}'")
            return f"Allowed to start with '{order[0]}'"

        self._check_item_in_order(prev, order, "previous item")

        prev_idx = order.index(prev)
        next_idx = order.index(next_item)

        if next_idx == prev_idx:
            raise ValueError(
                f"Already in '{prev}' phase. Do not re-invoke the skill."
            )
        if next_idx < prev_idx:
            raise ValueError(f"Cannot go backwards from '{prev}' to '{next_item}'")
        if next_idx > prev_idx + 1:
            skipped = order[prev_idx + 1 : next_idx]
            raise ValueError(f"Must complete {skipped} before '{next_item}'")

        return f"Phase is allowed to transition to '{next_item}'"

    # ── Review exhaustion ─────────────────────────────────────────

    _EXHAUSTION_MAP: dict[str, tuple[str, str]] = {
        "plan-review": ("plan_review", "status"),
        "test-review": ("test_review", "verdict"),
        "tests-review": ("test_review", "verdict"),
        "code-review": ("code_review", "status"),
    }

    def _is_review_exhausted(self, phase: str) -> bool:
        if phase in ("quality-check", "validate"):
            return (
                self.state.qa_specialist_count >= 3
                and self.state.quality_check_result == "Fail"
            )

        entry = self._EXHAUSTION_MAP.get(phase)
        if not entry:
            return False

        prefix, verdict_key = entry
        count = getattr(self.state, f"{prefix}_count")
        last = getattr(self.state, f"last_{prefix}")
        return count >= 3 and last is not None and last.get(verdict_key) == "Fail"

    # ── Skill handlers ────────────────────────────────────────────

    def _handle_continue(self) -> Decision:
        if self.current == "plan-review":
            raise ValueError(
                "Use '/plan-approved' to approve the plan, or '/revise-plan' to revise it."
            )

        if self.status == "completed":
            Resolver(self.config, self.state).auto_start_next()
            return "allow", f"Continuing after completed phase: {self.current}"

        if self.status == "in_progress":
            self.state.set_phase_completed(self.current)
            Resolver(self.config, self.state).auto_start_next()
            return "allow", f"Force-completed phase: {self.current}"

        raise ValueError(
            f"'/continue' cannot continue — current phase '{self.current}' has status '{self.status}'."
        )

    def _handle_plan_approved(self) -> Decision:
        if self.current != "plan-review":
            raise ValueError(
                "'/plan-approved' can only be used during plan-review. "
                f"Current phase: '{self.current}'"
            )

        if self.status == "completed":
            Resolver(self.config, self.state).auto_start_next(skip_checkpoint=True)
            return "allow", "Plan approved. Proceeding to next phase."

        if self.status == "in_progress" and self._is_review_exhausted("plan-review"):
            self.state.set_phase_completed("plan-review")
            Resolver(self.config, self.state).auto_start_next(skip_checkpoint=True)
            return (
                "allow",
                "Plan approved (after review exhaustion). Proceeding to next phase.",
            )

        raise ValueError(
            "'/plan-approved' requires plan-review to be at checkpoint (passed) or exhausted (3 fails). "
            f"Current status: {self.status}, review count: {self.state.plan_review_count}"
        )

    def _handle_revise_plan(self) -> Decision:
        if self.current != "plan-review":
            raise ValueError(
                "'/revise-plan' can only be used during plan-review. "
                f"Current phase: '{self.current}'"
            )

        is_checkpoint = self.status == "completed"
        is_exhausted = self.status == "in_progress" and self._is_review_exhausted(
            "plan-review"
        )

        if not is_checkpoint and not is_exhausted:
            raise ValueError(
                "'/revise-plan' requires plan-review to be at checkpoint (passed) or exhausted (3 fails). "
                f"Current status: {self.status}, review count: {self.state.plan_review_count}"
            )

        def _reopen(d: dict) -> None:
            for p in d.get("phases", []):
                if p["name"] == "plan-review":
                    p["status"] = "in_progress"
                    break
            plan = d.setdefault("plan", {})
            plan["revised"] = False
            plan["reviews"] = []

        self.state.update(_reopen)
        return (
            "allow",
            "Plan-review reopened for revision. Edit the plan, then re-invoke PlanReview.",
        )

    def _handle_reset_plan_review(self) -> Decision:
        if self.state.get("test_mode"):
            return "allow", "Test-mode reset allowed"
        raise ValueError("'/reset-plan-review' is only available in test mode.")

    # ── Transition validation ─────────────────────────────────────

    def _check_not_auto_phase(self) -> None:
        if self.config.is_auto_phase(self.next_phase):
            raise ValueError(
                f"'{self.next_phase}' is an auto-phase — it starts automatically after the previous phase completes. "
                f"Do not invoke it as a skill."
            )

    def _check_current_phase_done(self) -> None:
        if self.next_phase and self.status != "completed":
            if self.next_phase == self.current:
                raise ValueError(
                    f"Already in '{self.current}' phase. Complete the phase tasks instead of re-invoking the skill."
                )
            raise ValueError(
                f"Phase '{self.current}' is not completed. Finish it before transitioning to '{self.next_phase}'."
            )

    def _resolve_prev_for_ordering(self) -> str:
        """When current phase is an auto-phase, find the last completed skill-phase for ordering."""
        skill_phases = [p for p in self.phases if not self.config.is_auto_phase(p)]
        if not self.config.is_auto_phase(self.current):
            return self.current
        completed = [p["name"] for p in self.state.phases if p["status"] == "completed"]
        for p in reversed(completed):
            if p in skill_phases:
                return p
        return self.current

    def _get_skill_phases(self) -> list[str]:
        skill_phases = [p for p in self.phases if not self.config.is_auto_phase(p)]
        if not self.state.get("tdd", False):
            skill_phases = [
                p for p in skill_phases if p not in ("test-review", "tests-review")
            ]
        return skill_phases

    # ── Validate ──────────────────────────────────────────────────

    def validate(self) -> Decision:
        """Returns ("allow", message) or ("block", reason)."""
        try:
            # Skill command handlers
            if self.next_phase == "continue":
                return self._handle_continue()
            if self.next_phase == "plan-approved":
                return self._handle_plan_approved()
            if self.next_phase == "revise-plan":
                return self._handle_revise_plan()
            if self.next_phase == "reset-plan-review":
                return self._handle_reset_plan_review()

            self._check_not_auto_phase()

            # No phases yet — allow the first one
            if not self.current:
                message = self._validate_order(None, self.next_phase, self.phases)
                return "allow", message

            # Parallel explore + research
            if (
                self.current == "explore"
                and self.status == "in_progress"
                and self.next_phase == "research"
            ):
                return "allow", "Running Research in parallel with Explore"

            self._check_current_phase_done()

            skill_phases = self._get_skill_phases()
            prev = self._resolve_prev_for_ordering()
            message = self._validate_order(prev, self.next_phase, skill_phases)
            return "allow", message
        except ValueError as e:
            return "block", str(e)
