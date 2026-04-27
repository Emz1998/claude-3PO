"""AgentGuard — Validates agent invocation against phase and count restrictions."""

from typing import Literal

from lib.state_store import StateStore  # type: ignore
from lib.extractors import extract_agent_name  # type: ignore
from config import Config  # type: ignore


Decision = tuple[Literal["allow", "block"], str]


class AgentGuard:
    """Validate an Agent invocation against phase + per-agent count restrictions.

    The guard enforces two intertwined rules: only the agent expected for the
    current phase may run, and an agent may not exceed its configured
    max-invocations. ``validate()`` is the only public entry point;
    ``check_*`` helpers raise ``ValueError`` and ``validate`` catches them and
    converts to ``("block", reason)``.

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

    def is_parallel_research_allowed(self) -> bool:
        """True iff Explore is in-progress and the next agent is Research.

        Example:
            >>> guard.is_parallel_research_allowed()  # doctest: +SKIP
            True
        """
        explore = self.state.get_agent("Explore")
        return (
            explore is not None
            and explore.get("status") == "in_progress"
            and self.next_agent == "Research"
        )

    def resolve_parallel_phase(self) -> None:
        """
        Re-tag self.phase to ``explore`` when launching extra Explore agents during research.

        The user is allowed to spawn additional Explore agents even after the
        workflow has already advanced into the ``research`` phase. This helper
        rewrites ``self.phase`` so the downstream checks see ``explore`` and
        accept the Explore agent.

        Example:
            >>> guard.resolve_parallel_phase()  # doctest: +SKIP

        SideEffect:
            May reassign ``self.phase`` from ``research`` to ``explore``.
        """
        if (
            self.next_agent == "Explore"
            and self.phase == "research"
            and self.state.get_phase_status("explore") is not None
        ):
            self.phase = "explore"

    # ── Checks ────────────────────────────────────────────────────

    @property
    def phase_label(self) -> str:
        """Human-readable phase name, or a placeholder when no phase is active.

        Example:
            >>> guard.phase_label  # doctest: +SKIP
            'plan'
        """
        return self.phase or "(no phase active — workflow not started)"

    def check_expected_agent(self) -> None:
        """
        Verify the requested agent is the one this phase expects.

        Raises:
            ValueError: If the phase has no allowed agent, or the requested
                agent does not match the expected one.

        Example:
            >>> # Raises ValueError when the requested agent doesn't match the phase:
            >>> guard.check_expected_agent()  # doctest: +SKIP
        """
        expected = self.config.get_required_agent(self.phase)
        if not expected:
            raise ValueError(f"No agent allowed in phase: {self.phase_label}")
        if self.next_agent != expected:
            raise ValueError(
                f"Agent '{self.next_agent}' not allowed in phase: {self.phase_label}"
                f"\nExpected: {expected}"
            )

    def check_agent_count(self) -> None:
        """
        Reject the invocation if the agent has already hit its max-count.

        Raises:
            ValueError: If the agent has been invoked the maximum number of times.

        Example:
            >>> # Raises ValueError when the agent is at max-count:
            >>> guard.check_agent_count()  # doctest: +SKIP
        """
        max_allowed = self.config.get_agent_max_count(self.next_agent)
        actual = self.state.count_agents(self.next_agent)
        if actual >= max_allowed:
            raise ValueError(
                f"Agent '{self.next_agent}' at max ({max_allowed}) in phase: {self.phase}"
            )

    # ── Validate ──────────────────────────────────────────────────

    def validate(self) -> Decision:
        """
        Run all checks and return an allow/block decision.

        Order matters: the parallel Explore+Research short-circuit runs first, then
        the auto-rewrite of phase for extra Explore invocations, then the
        agent/count checks. Any ``ValueError`` raised by a check becomes a Block.

        Returns:
            Decision: ``("allow", message)`` if the agent may run, otherwise
            ``("block", reason)``.

        Example:
            >>> # When state has no current_phase, expect a block.
            >>> # AgentGuard({"tool_input": {"subagent_type": "Plan"}}, cfg, state).validate()[0]
            >>> # 'block'
        """
        try:
            # Parallel Research during Explore is explicitly allowed — the
            # short-circuit bypasses expected-agent/count checks because the
            # research track runs alongside rather than replacing explore.
            if self.phase == "explore" and self.is_parallel_research_allowed():
                return "allow", "Running Research in parallel with Explore"

            self.resolve_parallel_phase()
            self.check_expected_agent()
            self.check_agent_count()

            return "allow", f"{self.next_agent} agent allowed in phase: {self.phase}"
        except ValueError as e:
            return "block", str(e)
