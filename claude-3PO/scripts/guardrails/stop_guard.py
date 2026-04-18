"""StopGuard — Validates that workflow is complete before allowing session stop."""

from typing import Literal

from lib.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class StopGuard:
    """Validate that the workflow is fully complete before allowing session stop.

    Unlike the other guards, this one collects *all* failures across multiple
    independent checks (phases, tests, CI) and returns them joined — the goal
    is to give the operator one consolidated "still missing X, Y, Z" message
    rather than one error at a time. Test mode skips the tests/CI checks
    because those signals are simulated in test runs.

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

    def _check_phases(self) -> None:
        """
        Require every non-skipped workflow phase to be ``completed``.

        Raises:
            ValueError: If any required phase is missing from the completed set.

        Example:
            >>> # Raises ValueError when required phases are missing:
            >>> guard._check_phases()  # doctest: +SKIP
        """
        workflow_type = self.state.get("workflow_type", "build")
        workflow_phases = self.config.get_phases(workflow_type) or self.config.main_phases
        required = [p for p in workflow_phases if p not in self.skip]

        completed = {p["name"] for p in self.state.phases if p["status"] == "completed"}
        missing = [p for p in required if p not in completed]

        if missing:
            raise ValueError(f"Phases not completed: {missing}")

    def _check_tests(self) -> None:
        """
        Require tests to exist, have been executed, and the last review to Pass.

        Skipped entirely when both ``write-tests`` and ``test-review`` are in
        the skip list (the workflow opted out of testing).

        Raises:
            ValueError: If no tests were written, none were executed, or the
                last test-review verdict is not ``Pass``.

        Example:
            >>> # Raises ValueError when tests have not been executed yet:
            >>> guard._check_tests()  # doctest: +SKIP
        """
        if "write-tests" in self.skip and "test-review" in self.skip:
            return

        tests = self.state.tests

        if not tests.get("file_paths"):
            raise ValueError("No test files written")

        if not tests.get("executed"):
            raise ValueError("Tests not executed")

        last_review = self.state.last_test_review
        verdict = last_review.get("verdict") if last_review else None
        if verdict != "Pass":
            raise ValueError(f"Test review verdict: {verdict}, expected: Pass")

    def _check_ci(self) -> None:
        """
        Require CI to be ``passed``.

        Skipped when ``ci-check`` is in the skip list. ``failed`` and any
        other non-``passed`` status (including ``pending``) both block.

        Raises:
            ValueError: If CI status is anything other than ``passed``.

        Example:
            >>> # Raises ValueError when CI status is not 'passed':
            >>> guard._check_ci()  # doctest: +SKIP
        """
        if "ci-check" in self.skip:
            return

        status = self.state.ci.get("status", "pending")

        if status == "passed":
            return

        if status == "failed":
            raise ValueError("CI checks failed")

        raise ValueError(f"CI status: {status}, expected: passed")

    # ── Validate ──────────────────────────────────────────────────

    def validate(self) -> Decision:
        """
        Run every applicable check and return a consolidated decision.

        Unlike most guards, failures from each check are collected and joined
        with newlines so the operator sees the full list at once.

        Returns:
            Decision: ``("allow", "Workflow complete")`` if every check passed,
            otherwise ``("block", joined_failure_messages)``.

        Example:
            >>> decision, message = guard.validate()  # doctest: +SKIP
            >>> decision  # doctest: +SKIP
            'allow'
        """
        failures: list[str] = []

        # Always check phases; skip tests/CI in test mode (simulated, not real)
        checks = [self._check_phases]
        if not self.state.get("test_mode"):
            checks += [self._check_tests, self._check_ci]

        for check in checks:
            try:
                check()
            except ValueError as e:
                failures.append(str(e))

        if failures:
            return "block", "\n".join(failures)

        return "allow", "Workflow complete"
