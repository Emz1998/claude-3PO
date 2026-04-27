"""Resolver — Evaluates state after each tool call and resolves phase completion.

After a recorder writes raw data to state, the resolver checks completion
conditions for the current phase and auto-starts the next phase if needed.

A single dispatch table — ``_TOOL_RESOLVER_MAP`` — keeps per-phase resolution
table-driven. ``auto_start_next`` and ``_skip_tdd_phases`` together implement
the auto-advance machinery, including the ``--tdd``-off optimization that
hops over the ``write-tests`` phase when TDD is disabled. Phases flagged
``checkpoint: true`` (currently ``plan``) pause auto-advance so a human can
review before continuing.
"""

from lib.state_store import StateStore
from lib.paths import basenames
from models.state import DONE_STATUSES, TDD_PHASES
from config import Config


class Resolver:
    """Resolve phase completion based on current state.

    A fresh Resolver is constructed per hook call: it captures the
    current phase at construction time and dispatches to either an
    agent-phase resolver or a tool-phase resolver. Checkpoint phases
    (e.g. ``plan``) pause auto-advance so a human can intervene.

    Example:
        >>> Resolver(config, state)  # doctest: +SKIP
    """

    def __init__(self, config: Config, state: StateStore):
        """Bind the resolver to a config + state pair.

        Args:
            config (Config): Workflow configuration (phase order, checkpoint flags).
            state (StateStore): Session state to read and mutate.

        Example:
            >>> Resolver(config, state)  # doctest: +SKIP
        """
        self.config = config
        self.state = state
        self.phase = state.current_phase
        self.workflow_type = state.get("workflow_type", "implement")
        self.phases_ordered = (
            config.get_phases(self.workflow_type) or config.main_phases
        )

    # ══════════════════════════════════════════════════════════════
    # Agent-based phases
    # ══════════════════════════════════════════════════════════════

    def _is_required_agent_done(self, phase_name: str) -> bool:
        """True if the phase's required agent has run and every invocation completed.

        Returns ``True`` when the phase has no required agent (no gate), or
        when at least one invocation exists and all invocations have
        ``status=completed``. Used as a gate by agent-only phases and by
        ``_resolve_plan``, which adds its own file-written check on top.

        Args:
            phase_name (str): Phase whose required-agent slot to check.

        Returns:
            bool: True when the agent gate is satisfied.

        Example:
            >>> Resolver(config, state)._is_required_agent_done("plan")  # doctest: +SKIP
            True
        """
        agent_name = self.config.get_required_agent(phase_name)
        if not agent_name:
            return True
        agents = [a for a in self.state.agents if a.get("name") == agent_name]
        return bool(agents) and all(a.get("status") == "completed" for a in agents)

    def _resolve_agent_phase(self, phase_name: str) -> None:
        """Complete a phase when all its required agents have ``status=completed``.

        Args:
            phase_name (str): Phase whose required-agent slot to look up.

        Example:
            >>> Resolver(config, state)._resolve_agent_phase("explore")  # doctest: +SKIP
        """
        if not self.config.get_required_agent(phase_name):
            return
        if self._is_required_agent_done(phase_name):
            self.state.set_phase_completed(phase_name)

    # ══════════════════════════════════════════════════════════════
    # Tool resolvers (file writes, bash, tasks)
    # ══════════════════════════════════════════════════════════════

    # ── Plan ──────────────────────────────────────────────────────

    def _resolve_plan(self) -> None:
        """Complete ``plan`` when the planner agent has reported and the file is written.

        The agent gate runs first because a plan written without a
        completed planner means the recorder caught a stray write — we
        intentionally don't close the phase in that case so the planner
        gets a chance to actually run.

        Example:
            >>> Resolver(config, state)._resolve_plan()  # doctest: +SKIP
        """
        if not self._is_required_agent_done("plan"):
            return
        plan = self.state.plan
        if plan.get("written") and plan.get("file_path"):
            self.state.set_phase_completed("plan")

    # ── Write phases ──────────────────────────────────────────────

    def _resolve_write_code(self) -> None:
        """Complete ``write-code`` when every planned code file has been written.

        Example:
            >>> Resolver(config, state)._resolve_write_code()  # doctest: +SKIP
        """
        to_write = basenames(self.state.code_files_to_write)
        written = basenames(self.state.code_files.get("file_paths", []))
        if to_write and not (to_write - written):
            self.state.set_phase_completed("write-code")

    def _resolve_write_tests(self) -> None:
        """Complete ``write-tests`` when test files exist *and* have been executed.

        Example:
            >>> Resolver(config, state)._resolve_write_tests()  # doctest: +SKIP
        """
        tests = self.state.tests
        file_paths = tests.get("file_paths", [])
        if file_paths and tests.get("executed"):
            self.state.set_phase_completed("write-tests")

    def _resolve_report(self) -> None:
        """Complete ``write-report`` once ``state.report_written`` is set.

        Example:
            >>> Resolver(config, state)._resolve_report()  # doctest: +SKIP
        """
        if self.state.report_written:
            self.state.set_phase_completed("write-report")

    # ── Tasks ─────────────────────────────────────────────────────

    def _all_project_tasks_have_subtasks(self) -> bool:
        """Return True when every project task has at least one subtask.

        Example:
            >>> Resolver(config, state)._all_project_tasks_have_subtasks()  # doctest: +SKIP
        """
        ptasks = self.state.implement.project_tasks
        if not ptasks:
            return False
        return all(len(pt.get("subtasks", [])) >= 1 for pt in ptasks)

    def _resolve_create_tasks(self) -> None:
        """Complete ``create-tasks`` once every project task has a subtask.

        Example:
            >>> Resolver(config, state)._resolve_create_tasks()  # doctest: +SKIP
        """
        if self._all_project_tasks_have_subtasks():
            self.state.set_phase_completed("create-tasks")

    # ══════════════════════════════════════════════════════════════
    # Auto-start & workflow completion
    # ══════════════════════════════════════════════════════════════

    def _is_phase_ready_to_advance(self, skip_checkpoint: bool) -> bool:
        """Return True if the current phase is finished (completed/skipped) and may auto-advance.

        Phases flagged ``checkpoint: true`` in ``config.json`` (currently
        ``plan``) are human checkpoints and never auto-advance unless the
        caller explicitly opts in via ``skip_checkpoint``.

        Args:
            skip_checkpoint (bool): If True, bypass the checkpoint pause.

        Returns:
            bool: True if ``auto_start_next`` should proceed.

        Example:
            >>> Resolver(config, state)._is_phase_ready_to_advance(False)  # doctest: +SKIP
        """
        phase = self.state.current_phase
        if not phase or self.state.get_phase_status(phase) not in DONE_STATUSES:
            return False
        if self.config.is_checkpoint_phase(phase) and not skip_checkpoint:
            return False
        return True

    def _get_next_auto_phase(self) -> str | None:
        """Return the next auto-advance phase in the configured ordering, or None.

        Returns:
            str | None: Next phase name if auto-advance is allowed for it
            and we're not at the end of the workflow; otherwise ``None``.

        Example:
            >>> Resolver(config, state)._get_next_auto_phase()  # doctest: +SKIP
        """
        phase = self.state.current_phase
        phases = self.phases_ordered

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
        """Hop past test-related phases when TDD is disabled.

        When ``state.tdd`` is False, ``write-tests`` is skipped — there's no
        test scaffolding to write, so resolving it would block the workflow
        forever. Returns ``None`` if the next eligible phase isn't
        auto-advanceable, leaving the user to advance manually.

        Args:
            next_phase (str): Phase name returned by :meth:`_get_next_auto_phase`.

        Returns:
            str | None: ``next_phase`` unchanged if TDD is on or ``next_phase``
            isn't ``write-tests``; otherwise the first non-test auto-phase, or
            ``None`` if none qualifies.

        Example:
            >>> Resolver(config, state)._skip_tdd_phases("write-tests")  # doctest: +SKIP
        """
        if self.state.get("tdd", False) or next_phase != "write-tests":
            return next_phase

        phases = self.phases_ordered
        skip_idx = phases.index(self.state.current_phase) + 1

        # Hop past consecutive TDD-only phases.
        while skip_idx < len(phases) and phases[skip_idx] in TDD_PHASES:
            skip_idx += 1

        if skip_idx < len(phases) and self.config.is_auto_phase(phases[skip_idx]):
            return phases[skip_idx]
        return None

    def auto_start_next(self, skip_checkpoint: bool = False) -> None:
        """Open the next auto-advance phase if the current one is complete.

        Combines the readiness check, next-phase lookup, and TDD-skip
        into one entry point used by the main resolve cycle.

        Args:
            skip_checkpoint (bool): Skip the checkpoint pause (e.g. plan).

        Example:
            >>> Resolver(config, state).auto_start_next()  # doctest: +SKIP
        """
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
        """Flip the workflow to ``completed`` once every required phase is done.

        ``required`` excludes phases the user opted out of via ``--skip``
        and (when TDD is off) the test-only phases. Sets both
        ``status=completed`` and ``workflow_active=False`` so the session
        no longer claims a story id and other sessions can run.

        Example:
            >>> Resolver(config, state)._check_workflow_complete()  # doctest: +SKIP
        """
        if self.state.get("status") == "completed":
            return

        skip = self.state.get("skip", [])
        tdd = self.state.get("tdd", False)

        required = [p for p in self.phases_ordered if p not in skip]
        if not tdd:
            required = [p for p in required if p not in TDD_PHASES]

        done = set(self.state.done_phase_names())
        if all(p in done for p in required):
            self.state.set_many({"status": "completed", "workflow_active": False})

    # ══════════════════════════════════════════════════════════════
    # Main dispatch
    # ══════════════════════════════════════════════════════════════

    # Phases that resolve when their required agent has run.
    _AGENT_PHASES: frozenset[str] = frozenset({"explore", "research"})

    _TOOL_RESOLVER_MAP: dict[str, str] = {
        "plan": "_resolve_plan",
        "create-tasks": "_resolve_create_tasks",
        "write-tests": "_resolve_write_tests",
        "write-code": "_resolve_write_code",
        "write-report": "_resolve_report",
    }

    def resolve(self) -> None:
        """Main resolver — dispatch tool resolvers, then auto-advance.

        Order matters: agent gate runs before tool resolvers (some
        phases depend on agent records the tool resolvers don't touch),
        the parallel-explore special case fixes up explore status when
        ``research`` resolves first, and the workflow-complete check
        runs last so a freshly-completed final phase can flip the
        session.

        Example:
            >>> Resolver(config, state).resolve()  # doctest: +SKIP
        """
        self._dispatch_phase_resolver()
        self._dispatch_resolver(self._TOOL_RESOLVER_MAP)
        self._maybe_resolve_parallel_explore()
        self.auto_start_next()
        self._check_workflow_complete()

    def _dispatch_phase_resolver(self) -> None:
        """Route the current phase to its agent-completion resolver.

        Tool-phase resolvers run separately via ``_TOOL_RESOLVER_MAP``;
        this method only handles the agent-gated phases (``explore`` /
        ``research``).

        Example:
            >>> Resolver(config, state)._dispatch_phase_resolver()  # doctest: +SKIP
        """
        if self.phase in self._AGENT_PHASES:
            self._resolve_agent_phase(self.phase)

    def _dispatch_resolver(self, mapping: dict[str, str]) -> None:
        """Look up the resolver method for the current phase and invoke it.

        Example:
            >>> Resolver(config, state)._dispatch_resolver({"plan": "_resolve_plan"})  # doctest: +SKIP
        """
        method_name = mapping.get(self.phase)
        if method_name:
            getattr(self, method_name)()

    def _maybe_resolve_parallel_explore(self) -> None:
        """Force-resolve explore when research finished while explore was still in-progress.

        Parallel ``explore`` + ``research`` is intentional — research can
        start while explore is still running. But the resolver only fires
        for the *current* phase, so when the hook runs for research,
        explore would never be re-checked unless we do it here.

        Example:
            >>> Resolver(config, state)._maybe_resolve_parallel_explore()  # doctest: +SKIP
        """
        if (
            self.phase == "research"
            and self.state.get_phase_status("explore") == "in_progress"
        ):
            self._resolve_agent_phase("explore")


# ══════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════


def resolve(config: Config, state: StateStore) -> None:
    """Module-level convenience wrapper around ``Resolver(config, state).resolve()``.

    Args:
        config (Config): Workflow configuration.
        state (StateStore): Session state to resolve against.

    Example:
        >>> from config import Config
        >>> from lib.state_store import StateStore
        >>> resolve(Config(), StateStore("/tmp/state.json"))  # doctest: +SKIP
    """
    Resolver(config, state).resolve()
