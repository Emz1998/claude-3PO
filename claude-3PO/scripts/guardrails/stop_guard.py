"""StopGuard — Validates that workflow is complete before allowing session stop."""

from typing import Literal

from lib.state_store import StateStore  # type: ignore
from config import Config  # type: ignore


Decision = tuple[Literal["allow", "block"], str]


class StopGuard:
    """Validate that the workflow is fully complete before allowing session stop.

    In the trimmed 7-phase MVP only the phase-completion check remains —
    tests and CI gating were removed when the test-review/CI-check phases
    were dropped. Phase-completion failures surface to the operator with a
    consolidated "still missing X, Y, Z" message.

    Example:
        >>> guard = StopGuard(config, state)  # doctest: +SKIP
        >>> decision, message = guard.validate()  # doctest: +SKIP
    """

    def __init__(self, config: Config, state: StateStore):
        """
        Cache config, state, and the workflow's per-session skip list.

        Args:
            config (Config): Workflow configuration.
            state (StateStore): Mutable workflow state snapshot.

        Example:
            >>> guard = StopGuard(config, state)  # doctest: +SKIP
            >>> guard.skip  # doctest: +SKIP
            []
        """
        self.config = config
        self.state = state
        self.skip = state.load().get("skip", [])

    # ── Checks ────────────────────────────────────────────────────

    def check_phases(self) -> None:
        """
        Require every non-skipped workflow phase to be ``completed``.

        Raises:
            ValueError: If any required phase is missing from the completed set.

        Example:
            >>> # Raises ValueError when required phases are missing:
            >>> guard.check_phases()  # doctest: +SKIP
        """
        workflow_type = self.state.get("workflow_type", "implement")
        workflow_phases = (
            self.config.get_phases(workflow_type) or self.config.main_phases
        )
        required = [p for p in workflow_phases if p not in self.skip]

        completed = {p["name"] for p in self.state.phases if p["status"] == "completed"}
        missing = [p for p in required if p not in completed]

        if missing:
            raise ValueError(f"Phases not completed: {missing}")

    # ── Validate ──────────────────────────────────────────────────

    def validate(self) -> Decision:
        """
        Run the phase-completion check and return a decision.

        Returns:
            Decision: ``("allow", "Workflow complete")`` if every required phase
            is completed, otherwise ``("block", reason)``.

        Example:
            >>> decision, message = guard.validate()  # doctest: +SKIP
            >>> decision  # doctest: +SKIP
            'allow'
        """
        try:
            self.check_phases()
        except ValueError as e:
            return "block", str(e)
        return "allow", "Workflow complete"
