"""AgentGuard — Validates agent invocation against phase and count restrictions."""

from typing import Literal

from lib.state_store import StateStore
from lib.extractors import extract_agent_name
from lib.paths import basenames
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class AgentGuard:
    """Validate an Agent invocation against phase + per-agent count restrictions.

    The guard enforces three intertwined rules: only the agent expected for the
    current phase may run, an agent may not exceed its configured max-invocations,
    and re-invoking a *reviewer* agent after a Fail verdict requires that all
    flagged files have been revised first. ``validate()`` is the only public
    method; private ``_check_*`` helpers raise ``ValueError`` and ``validate``
    catches/converts them to ``("block", reason)``.

    Example:
        >>> guard = AgentGuard(hook_input, config, state)  # doctest: +SKIP
        >>> decision, message = guard.validate()  # doctest: +SKIP
    """

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        """
        Cache the phase, target agent name, and dependencies.

        Args:
            hook_input (dict): Raw PreToolUse hook payload.
            config (Config): Workflow configuration (phase→agent mapping, max counts).
            state (StateStore): Mutable workflow state snapshot.

        Example:
            >>> guard = AgentGuard(hook_input, config, state)  # doctest: +SKIP
            >>> guard.next_agent  # doctest: +SKIP
            'Plan'
        """
        self.config = config
        self.state = state
        self.phase = state.current_phase
        self.next_agent = extract_agent_name(hook_input)

    # ── Parallel explore+research ─────────────────────────────────

    def _is_parallel_research_allowed(self) -> bool:
        """True iff Explore is in-progress and the next agent is Research.

        Example:
            >>> guard._is_parallel_research_allowed()  # doctest: +SKIP
            True
        """
        explore = self.state.get_agent("Explore")
        return (
            explore is not None
            and explore.get("status") == "in_progress"
            and self.next_agent == "Research"
        )

    def _resolve_parallel_phase(self) -> None:
        """
        Re-tag self.phase to ``explore`` when launching extra Explore agents during research.

        The user is allowed to spawn additional Explore agents even after the
        workflow has already advanced into the ``research`` phase. This helper
        rewrites ``self.phase`` so the downstream checks see ``explore`` and
        accept the Explore agent.

        Example:
            >>> guard._resolve_parallel_phase()  # doctest: +SKIP
        """
        if (
            self.next_agent == "Explore"
            and self.phase == "research"
            and self.state.get_phase_status("explore") is not None
        ):
            self.phase = "explore"

    # ── Checks ────────────────────────────────────────────────────

    @property
    def _phase_label(self) -> str:
        """Human-readable phase name, or a placeholder when no phase is active.

        Example:
            >>> guard._phase_label  # doctest: +SKIP
            'plan'
        """
        return self.phase or "(no phase active — workflow not started)"

    def _check_expected_agent(self) -> None:
        """
        Verify the requested agent is the one this phase expects.

        Raises:
            ValueError: If the phase has no allowed agent, or the requested
                agent does not match the expected one.

        Example:
            >>> # Raises ValueError when the requested agent doesn't match the phase:
            >>> guard._check_expected_agent()  # doctest: +SKIP
        """
        expected = self.config.get_required_agent(self.phase)
        if not expected:
            raise ValueError(f"No agent allowed in phase: {self._phase_label}")
        if self.next_agent != expected:
            raise ValueError(
                f"Agent '{self.next_agent}' not allowed in phase: {self._phase_label}"
                f"\nExpected: {expected}"
            )

    def _check_agent_count(self) -> None:
        """
        Reject the invocation if the agent has already hit its max-count.

        Raises:
            ValueError: If the agent has been invoked the maximum number of times.

        Example:
            >>> # Raises ValueError when the agent is at max-count:
            >>> guard._check_agent_count()  # doctest: +SKIP
        """
        max_allowed = self.config.get_agent_max_count(self.next_agent)
        actual = self.state.count_agents(self.next_agent)
        if actual >= max_allowed:
            raise ValueError(
                f"Agent '{self.next_agent}' at max ({max_allowed}) in phase: {self.phase}"
            )

    def _check_plan_revision_done(self) -> None:
        """
        Require that the plan was revised before re-running PlanReview.

        Raises:
            ValueError: If ``state.plan_revised`` is False.

        Example:
            >>> # Raises ValueError when the plan hasn't been revised yet:
            >>> guard._check_plan_revision_done()  # doctest: +SKIP
        """
        if self.state.plan_revised is False:
            raise ValueError("Plan must be revised before re-invoking PlanReview")

    def _all_revised(self, to_revise: list[str], revised: list[str]) -> bool:
        """True iff every flagged file has been revised (compared by basename).

        Example:
            >>> guard._all_revised(["src/a.py"], ["a.py"])  # doctest: +SKIP
            True
        """
        return bool(to_revise) and not (
            basenames(to_revise) - basenames(revised)
        )

    def _check_test_revision_done(self) -> None:
        """
        Require all flagged test files revised before re-running TestReviewer.

        Only enforced when the previous test-review verdict was ``Fail`` —
        otherwise there's nothing to revise.

        Raises:
            ValueError: If files flagged by the last review remain unrevised.

        Example:
            >>> # Raises ValueError when flagged tests still need revision:
            >>> guard._check_test_revision_done()  # doctest: +SKIP
        """
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
        """
        Require all flagged code files revised before re-running CodeReviewer.

        Only enforced when the previous code-review status was ``Fail``.

        Raises:
            ValueError: If files flagged by the last review remain unrevised.

        Example:
            >>> # Raises ValueError when flagged code files still need revision:
            >>> guard._check_code_revision_done()  # doctest: +SKIP
        """
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
        """Dispatch to the per-reviewer revision check matching phase + agent.

        Example:
            >>> guard._check_revision_done()  # doctest: +SKIP
        """
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
        """
        Run all checks and return an allow/block decision.

        Order matters: the parallel Explore+Research short-circuit runs first, then
        the auto-rewrite of phase for extra Explore invocations, then the
        agent/count/revision checks. Any ``ValueError`` raised by a private check
        becomes a Block.

        Returns:
            Decision: ``("allow", message)`` if the agent may run, otherwise
            ``("block", reason)``.

        Example:
            >>> # When state has no current_phase, expect a block.
            >>> # AgentGuard({"tool_input": {"subagent_type": "Plan"}}, cfg, state).validate()[0]
            >>> # 'block'
        """
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
