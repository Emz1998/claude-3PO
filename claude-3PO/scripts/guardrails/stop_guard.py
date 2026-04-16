"""StopGuard — Validates that workflow is complete before allowing session stop."""

from typing import Literal

from lib.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class StopGuard:
    """Validate that all workflow requirements are met before stopping."""

    def __init__(self, config: Config, state: StateStore):
        self.config = config
        self.state = state
        self.skip = state.load().get("skip", [])

    # ── Checks ────────────────────────────────────────────────────

    def _check_phases(self) -> None:
        workflow_type = self.state.get("workflow_type", "build")
        workflow_phases = self.config.get_phases(workflow_type) or self.config.main_phases
        required = [p for p in workflow_phases if p not in self.skip]

        completed = {p["name"] for p in self.state.phases if p["status"] == "completed"}
        missing = [p for p in required if p not in completed]

        if missing:
            raise ValueError(f"Phases not completed: {missing}")

    def _check_tests(self) -> None:
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
        """Returns ("allow", message) or ("block", reason)."""
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
