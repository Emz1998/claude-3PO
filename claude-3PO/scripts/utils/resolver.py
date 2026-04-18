"""Resolver — Evaluates state after each tool call and resolves phase completion.

After a recorder writes raw data to state, the resolver checks completion
conditions for the current phase and auto-starts the next phase if needed.

Two parallel dispatch tables — ``_PHASE_RESOLVER_MAP`` and
``_TOOL_RESOLVER_MAP`` — keep the per-phase resolution logic table-driven
rather than buried in long if/elif chains. ``auto_start_next`` and
``_skip_tdd_phases`` together implement the auto-advance machinery,
including the ``--tdd``-off optimization that hops over the
``write-tests`` / ``test-review`` phases when TDD is disabled.
"""

from typing import Literal

from lib.state_store import StateStore
from lib.paths import basenames
from config import Config


class Resolver:
    """Resolve phase completion based on current state.

    A fresh Resolver is constructed per hook call: it captures the
    current phase at construction time and runs both dispatch maps
    against it. The maps split phase-driven resolvers (e.g. score-based
    review checks) from tool-driven resolvers (e.g. plan-file written)
    so each can be edited independently.

    Example:
        >>> Resolver(config, state)  # doctest: +SKIP
    """

    def __init__(self, config: Config, state: StateStore):
        """Bind the resolver to a config + state pair.

        Args:
            config (Config): Workflow configuration (phase order, thresholds).
            state (StateStore): Session state to read and mutate.

        Example:
            >>> Resolver(config, state)  # doctest: +SKIP
        """
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
        """Raise unless both confidence and quality clear their thresholds.

        Returning ``True`` means *no* revision is needed (the review passed).
        Failure is signalled by ``ValueError`` rather than a return value
        so the caller can short-circuit cleanly with a try/except — it's
        the cleanest way to surface *which* threshold failed without
        returning a tuple of booleans.

        Args:
            file_type (Literal): Which threshold set to consult.
            confidence (int): Reviewer's confidence score.
            quality (int): Reviewer's quality score.

        Returns:
            bool: Always ``True`` on success (raises otherwise).

        Raises:
            ValueError: When either threshold is unmet, with a message
                naming the failing dimension.

        Example:
            >>> Resolver(config, state)._is_revision_needed("plan", 9, 9)  # doctest: +SKIP
        """
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
        """Get scores from the latest review if it hasn't been resolved yet.

        Returns ``None`` when the review is missing, already has a status,
        or both scores are zero (treated as "not yet scored" to avoid a
        spurious failure on a stub review).

        Args:
            last_getter (str): Name of the StateStore property holding the
                latest review (e.g. ``"last_plan_review"``).

        Returns:
            tuple[int, int] | None: ``(confidence, quality)`` or ``None``
            if there's nothing to resolve.

        Example:
            >>> Resolver(config, state)._get_pending_scores("last_plan_review")  # doctest: +SKIP
        """
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
        """Stamp the latest review ``Fail`` and reopen plan revision if needed.

        Example:
            >>> Resolver(config, state)._mark_review_failed("plan", "set_last_plan_review_status")  # doctest: +SKIP
        """
        getattr(self.state, status_setter)("Fail")
        if file_type == "plan":
            self.state.set_plan_revised(False)

    def _mark_review_passed(self, status_setter: str, phase_name: str) -> None:
        """Stamp the latest review ``Pass`` and complete the phase.

        Example:
            >>> Resolver(config, state)._mark_review_passed("set_last_plan_review_status", "plan-review")  # doctest: +SKIP
        """
        getattr(self.state, status_setter)("Pass")
        self.state.set_phase_completed(phase_name)

    def _resolve_score_review(
        self,
        file_type: Literal["plan", "code"],
        last_getter: str,
        status_setter: str,
        phase_name: str,
    ) -> None:
        """Generic score-based review resolver shared by plan and code reviews.

        Args:
            file_type (Literal): Threshold bucket — ``"plan"`` or ``"code"``.
            last_getter (str): StateStore property name for the latest review.
            status_setter (str): StateStore method name to stamp the verdict.
            phase_name (str): Phase to complete on a Pass.

        Example:
            >>> Resolver(config, state)._resolve_score_review("plan", "last_plan_review", "set_last_plan_review_status", "plan-review")  # doctest: +SKIP
        """
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
        """Resolve the ``plan-review`` phase against plan score thresholds.

        Example:
            >>> Resolver(config, state)._resolve_plan_review()  # doctest: +SKIP
        """
        self._resolve_score_review(
            "plan", "last_plan_review", "set_last_plan_review_status", "plan-review"
        )

    def _resolve_code_review(self) -> None:
        """Resolve the ``code-review`` phase against code score thresholds.

        Example:
            >>> Resolver(config, state)._resolve_code_review()  # doctest: +SKIP
        """
        self._resolve_score_review(
            "code", "last_code_review", "set_last_code_review_status", "code-review"
        )

    # ── Verdict-based reviews ─────────────────────────────────────

    def _resolve_test_review(self) -> None:
        """Complete a test-review phase when its latest verdict is ``Pass``.

        The current phase may be either ``test-review`` or its alias
        ``tests-review`` — both are accepted so older configs keep working.
        Falls back to closing the canonical ``test-review`` name when the
        current phase is something else (defensive).

        Example:
            >>> Resolver(config, state)._resolve_test_review()  # doctest: +SKIP
        """
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
        """Complete the ``quality-check`` phase when its result is ``Pass``.

        Example:
            >>> Resolver(config, state)._resolve_quality_check()  # doctest: +SKIP
        """
        if self.state.quality_check_result == "Pass":
            self.state.set_phase_completed("quality-check")

    def _resolve_validate(self) -> None:
        """Complete the ``validate`` phase when the quality result is ``Pass``.

        Example:
            >>> Resolver(config, state)._resolve_validate()  # doctest: +SKIP
        """
        if self.state.quality_check_result == "Pass":
            self.state.set_phase_completed("validate")

    # ── Agent-based phases ────────────────────────────────────────

    def _resolve_agent_phase(self, phase_name: str) -> None:
        """Complete a phase when all its required agents have ``status=completed``.

        Args:
            phase_name (str): Phase whose required-agent slot to look up.

        Example:
            >>> Resolver(config, state)._resolve_agent_phase("explore")  # doctest: +SKIP
        """
        agent_name = self.config.get_required_agent(phase_name)
        if not agent_name:
            return
        agents = [a for a in self.state.agents if a.get("name") == agent_name]
        if agents and all(a.get("status") == "completed" for a in agents):
            self.state.set_phase_completed(phase_name)

    def _resolve_explore(self) -> None:
        """Resolve the ``explore`` phase via :meth:`_resolve_agent_phase`.

        Example:
            >>> Resolver(config, state)._resolve_explore()  # doctest: +SKIP
        """
        self._resolve_agent_phase("explore")

    def _resolve_research(self) -> None:
        """Resolve the ``research`` phase via :meth:`_resolve_agent_phase`.

        Example:
            >>> Resolver(config, state)._resolve_research()  # doctest: +SKIP
        """
        self._resolve_agent_phase("research")

    # ── Specs doc-based phases ───────────────────────────────────

    def _resolve_doc_phase(self, phase_name: str, doc_key: str) -> None:
        """Generic doc-phase resolver: complete iff the doc was written.

        Args:
            phase_name (str): Phase to complete.
            doc_key (str): Key under ``state.docs`` to inspect.

        Example:
            >>> Resolver(config, state)._resolve_doc_phase("vision", "product_vision")  # doctest: +SKIP
        """
        if self.state.is_doc_written(doc_key):
            self.state.set_phase_completed(phase_name)

    def _resolve_vision(self) -> None:
        """Complete ``vision`` once ``state.docs.product_vision`` is written.

        Example:
            >>> Resolver(config, state)._resolve_vision()  # doctest: +SKIP
        """
        self._resolve_doc_phase("vision", "product_vision")

    def _resolve_decision(self) -> None:
        """Complete ``decision`` once ``state.docs.decisions`` is written.

        Example:
            >>> Resolver(config, state)._resolve_decision()  # doctest: +SKIP
        """
        self._resolve_doc_phase("decision", "decisions")

    def _resolve_architect(self) -> None:
        """Complete ``architect`` once ``state.docs.architecture`` is written.

        Example:
            >>> Resolver(config, state)._resolve_architect()  # doctest: +SKIP
        """
        self._resolve_doc_phase("architect", "architecture")

    def _resolve_backlog(self) -> None:
        """Complete ``backlog`` once ``state.docs.backlog`` is written.

        Example:
            >>> Resolver(config, state)._resolve_backlog()  # doctest: +SKIP
        """
        self._resolve_doc_phase("backlog", "backlog")

    def _resolve_strategy(self) -> None:
        """Resolve the ``strategy`` phase via :meth:`_resolve_agent_phase`.

        Example:
            >>> Resolver(config, state)._resolve_strategy()  # doctest: +SKIP
        """
        self._resolve_agent_phase("strategy")

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
        agent_name = self.config.get_required_agent("plan")
        if agent_name:
            agents = [a for a in self.state.agents if a.get("name") == agent_name]
            if not agents or not all(a.get("status") == "completed" for a in agents):
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

    def _all_tasks_created(self) -> bool:
        """Return True when every planned task subject has a created counterpart.

        Example:
            >>> Resolver(config, state)._all_tasks_created()  # doctest: +SKIP
        """
        planned = set(self.state.tasks)
        created = set(self.state.created_tasks)
        return bool(planned) and not (planned - created)

    def _all_project_tasks_have_subtasks(self) -> bool:
        """Return True when every project task has at least one subtask.

        Example:
            >>> Resolver(config, state)._all_project_tasks_have_subtasks()  # doctest: +SKIP
        """
        ptasks = self.state.project_tasks
        if not ptasks:
            return False
        return all(len(pt.get("subtasks", [])) >= 1 for pt in ptasks)

    def _resolve_create_tasks(self) -> None:
        """Resolve ``create-tasks`` differently for ``implement`` vs ``build``.

        ``implement`` workflows decompose project tasks into subtasks, so
        completion means every project task has at least one subtask.
        ``build`` workflows track flat tasks, so completion means every
        planned task subject has been created.

        Example:
            >>> Resolver(config, state)._resolve_create_tasks()  # doctest: +SKIP
        """
        workflow_type = self.state.get("workflow_type", "build")
        if workflow_type == "implement":
            if self._all_project_tasks_have_subtasks():
                self.state.set_phase_completed("create-tasks")
        else:
            if self._all_tasks_created():
                self.state.set_phase_completed("create-tasks")

    # ── Delivery ──────────────────────────────────────────────────

    def _resolve_pr_create(self) -> None:
        """Complete ``pr-create`` once a PR number has been recorded.

        Example:
            >>> Resolver(config, state)._resolve_pr_create()  # doctest: +SKIP
        """
        if self.state.pr_status == "created":
            self.state.set_phase_completed("pr-create")

    def _resolve_ci_check(self) -> None:
        """Complete ``ci-check`` once CI is flagged passed.

        Example:
            >>> Resolver(config, state)._resolve_ci_check()  # doctest: +SKIP
        """
        if self.state.ci_status == "passed":
            self.state.set_phase_completed("ci-check")

    # ══════════════════════════════════════════════════════════════
    # Auto-start & workflow completion
    # ══════════════════════════════════════════════════════════════

    def _is_phase_ready_to_advance(self, skip_checkpoint: bool) -> bool:
        """Return True if the current phase is finished (completed/skipped) and may auto-advance.

        ``plan-review`` is special — it's a human checkpoint and never
        auto-advances unless the caller explicitly opts in via
        ``skip_checkpoint``.

        Args:
            skip_checkpoint (bool): If True, bypass the plan-review pause.

        Returns:
            bool: True if ``auto_start_next`` should proceed.

        Example:
            >>> Resolver(config, state)._is_phase_ready_to_advance(False)  # doctest: +SKIP
        """
        phase = self.state.current_phase
        if not phase or self.state.get_phase_status(phase) not in ("completed", "skipped"):
            return False
        if phase == "plan-review" and not skip_checkpoint:
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
        """Hop past test-related phases when TDD is disabled.

        When ``state.tdd`` is False, ``write-tests`` and the various
        ``*-review`` aliases that follow it are skipped — there's no test
        scaffolding to write or review, so resolving them would block the
        workflow forever. Returns ``None`` if the next eligible phase
        isn't auto-advanceable, leaving the user to advance manually.

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
        """Open the next auto-advance phase if the current one is complete.

        Combines the readiness check, next-phase lookup, and TDD-skip
        into one entry point used by the main resolve cycle.

        Args:
            skip_checkpoint (bool): Skip the plan-review human checkpoint.

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

        completed = {
            p["name"] for p in self.state.phases
            if p["status"] in ("completed", "skipped")
        }
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
        "vision": "_resolve_vision",
        "strategy": "_resolve_strategy",
        "decision": "_resolve_decision",
        "architect": "_resolve_architect",
        "backlog": "_resolve_backlog",
    }

    _TOOL_RESOLVER_MAP: dict[str, str] = {
        "plan": "_resolve_plan",
        "create-tasks": "_resolve_create_tasks",
        "write-tests": "_resolve_write_tests",
        "write-code": "_resolve_write_code",
        "pr-create": "_resolve_pr_create",
        "ci-check": "_resolve_ci_check",
        "write-report": "_resolve_report",
    }

    def resolve(self) -> None:
        """Main resolver — dispatch phase + tool resolvers, then auto-advance.

        Order matters: phase resolvers run before tool resolvers (some
        phases depend on agent records the tool resolvers don't touch),
        the parallel-explore special case fixes up explore status when
        ``research`` resolves first, and the workflow-complete check
        runs last so a freshly-completed final phase can flip the
        session.

        Example:
            >>> Resolver(config, state).resolve()  # doctest: +SKIP
        """
        self._dispatch_resolver(self._PHASE_RESOLVER_MAP)
        self._dispatch_resolver(self._TOOL_RESOLVER_MAP)
        self._maybe_resolve_parallel_explore()
        self.auto_start_next()
        self._check_workflow_complete()

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
            self._resolve_explore()


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
        >>> resolve(Config(), StateStore("/tmp/state.jsonl"))  # doctest: +SKIP
    """
    Resolver(config, state).resolve()
