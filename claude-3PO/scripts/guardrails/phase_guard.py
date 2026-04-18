"""PhaseGuard — validates phase transitions triggered by Skill invocations.

**Pure validator** — never mutates state and never calls the resolver. Each
``_handle_*`` method only returns a Decision describing whether the transition
is legal; dispatchers are responsible for applying the side effects via
``Recorder.apply_phase_skill`` after Allow.
"""

from typing import Literal

from lib.state_store import StateStore
from lib.extractors import extract_skill_name
from models.state import DONE_STATUSES
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class PhaseGuard:
    """Validate a phase transition triggered by a Skill invocation.

    Two transition models live side-by-side:

    - **Ordered transitions** — most skills must follow ``self.phases`` in order,
      with no skipping and no going back. Auto-phases (those that start
      automatically) cannot be invoked as skills at all.
    - **Special skills** — ``/continue``, ``/plan-approved``, ``/revise-plan``,
      and ``/reset-plan-review`` each have their own ``_handle_*`` method
      that returns a Decision based on phase + status invariants
      (e.g. ``/plan-approved`` requires plan-review to be at checkpoint or
      review-exhausted).

    The class is a **pure validator** — handlers no longer mutate state. After
    Allow, dispatchers apply state effects via :meth:`Recorder.apply_phase_skill`.

    Example:
        >>> guard = PhaseGuard(hook_input, config, state)  # doctest: +SKIP
        >>> decision, message = guard.validate()  # doctest: +SKIP
    """

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        """
        Cache phase, status, target skill, and the workflow's ordered phase list.

        Args:
            hook_input (dict): Raw PreToolUse hook payload.
            config (Config): Workflow configuration (phase ordering, auto-phase flags).
            state (StateStore): Mutable workflow state snapshot.

        Example:
            >>> guard = PhaseGuard(hook_input, config, state)  # doctest: +SKIP
            >>> guard.next_phase  # doctest: +SKIP
            'plan'
        """
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.tool_name = hook_input.get("tool_name", "")
        self.current = state.current_phase
        self.status = state.get_phase_status(self.current)
        self.next_phase = extract_skill_name(hook_input)
        self.phases = self._get_workflow_phases()

    def _get_workflow_phases(self) -> list[str]:
        """Return the phase list for the current workflow type (build / implement / etc.).

        Example:
            >>> phases = guard._get_workflow_phases()  # doctest: +SKIP
        """
        workflow_type = self.state.get("workflow_type", "build")
        phases = self.config.get_phases(workflow_type)
        return phases if phases else self.config.main_phases

    # ── Order validation ──────────────────────────────────────────

    def _check_item_in_order(self, item: str, order: list[str], label: str) -> None:
        """
        Confirm ``item`` appears in ``order``.

        Args:
            item (str): Item to check.
            order (list[str]): Reference ordered list.
            label (str): Human-readable label used in the error message.

        Raises:
            ValueError: If ``item`` is not in ``order``.

        Example:
            >>> # Raises ValueError when the item is missing from order:
            >>> guard._check_item_in_order("test", ["plan", "code"], "phase")  # doctest: +SKIP
        """
        if item not in order:
            raise ValueError(f"Invalid {label} '{item}'")

    def _validate_order(
        self, prev: str | None, next_item: str, order: list[str]
    ) -> str:
        """
        Enforce strict forward-by-one ordering against ``order``.

        Used for both phase ordering (with current-phase as ``prev``) and skill
        ordering. The first transition (``prev is None``) must hit ``order[0]``;
        subsequent transitions must advance by exactly one position — equal index
        means "already entered", lower index means "going backwards", higher than
        +1 means "skipping phases".

        Args:
            prev (str | None): Previous item, or ``None`` for first transition.
            next_item (str): Item being transitioned to.
            order (list[str]): Reference order.

        Returns:
            str: Success message describing the allowed transition.

        Raises:
            ValueError: If the transition violates the ordering invariants.

        Example:
            >>> guard._validate_order("plan", "code", ["plan", "code"])  # doctest: +SKIP
            "Phase is allowed to transition to 'code'"
        """
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
                f"Cannot re-invoke '{prev}'. The phase has already been entered — "
                f"advance to the next phase, or complete its tasks instead of restarting it."
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
        """
        True iff a review phase has hit 3 failed attempts.

        ``quality-check`` / ``validate`` use a separate counter
        (``qa_specialist_count`` + ``quality_check_result``). Other review
        phases lookup their (count_attr, verdict_key) pair in
        ``_EXHAUSTION_MAP``.

        Args:
            phase (str): Review phase name.

        Returns:
            bool: ``True`` if the phase has 3+ failures and the last review failed.

        Example:
            >>> guard._is_review_exhausted("plan-review")  # doctest: +SKIP
            False
        """
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
        """
        Validate ``/continue`` — advance past the current phase.

        Pure: returns a Decision; the dispatcher is responsible for the
        actual phase advance via Recorder.

        Returns:
            Decision: Allow if the phase is completed or in_progress (which
            counts as a force-complete). Block in plan-review (use
            ``/plan-approved`` or ``/revise-plan`` instead).

        Raises:
            ValueError: If used in plan-review or when the current phase has
                no advance-able status.

        Example:
            >>> decision, message = guard._handle_continue()  # doctest: +SKIP
        """
        if self.current == "plan-review":
            raise ValueError(
                "Use '/plan-approved' to approve the plan, or '/revise-plan' to revise it."
            )
        if self.status == "completed":
            return "allow", f"Continuing after completed phase: {self.current}"
        if self.status == "in_progress":
            return "allow", f"Force-completed phase: {self.current}"
        raise ValueError(
            f"'/continue' cannot continue — current phase '{self.current}' has status '{self.status}'."
        )

    def _handle_plan_approved(self) -> Decision:
        """
        Validate ``/plan-approved`` — operator overrides plan-review to proceed.

        Pure: returns a Decision; the dispatcher applies the phase advance.
        Allowed when plan-review is completed (Pass at checkpoint) OR when
        review is exhausted (3 fails) — the latter is the operator's escape
        hatch from a stuck reviewer.

        Returns:
            Decision: Allow if at checkpoint or review-exhausted, otherwise Block.

        Raises:
            ValueError: If invoked outside plan-review or in any other state.

        Example:
            >>> decision, message = guard._handle_plan_approved()  # doctest: +SKIP
        """
        if self.current != "plan-review":
            raise ValueError(
                "'/plan-approved' can only be used during plan-review. "
                f"Current phase: '{self.current}'"
            )
        if self.status == "completed":
            return "allow", "Plan approved. Proceeding to next phase."
        if self.status == "in_progress" and self._is_review_exhausted("plan-review"):
            return (
                "allow",
                "Plan approved (after review exhaustion). Proceeding to next phase.",
            )
        raise ValueError(
            "'/plan-approved' requires plan-review to be at checkpoint (passed) or exhausted (3 fails). "
            f"Current status: {self.status}, review count: {self.state.plan_review_count}"
        )

    def _handle_revise_plan(self) -> Decision:
        """
        Validate ``/revise-plan`` — reopen plan-review for another revision pass.

        Pure: returns a Decision; the dispatcher reopens the phase. Allowed
        under the same conditions as ``/plan-approved``: checkpoint or review
        exhaustion.

        Returns:
            Decision: Allow when plan-review is at checkpoint or exhausted,
            otherwise Block.

        Raises:
            ValueError: If invoked outside plan-review or in any other state.

        Example:
            >>> decision, message = guard._handle_revise_plan()  # doctest: +SKIP
        """
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
        return (
            "allow",
            "Plan-review reopened for revision. Edit the plan, then re-invoke PlanReview.",
        )

    def _handle_reset_plan_review(self) -> Decision:
        """
        Validate ``/reset-plan-review`` — test-mode-only escape hatch.

        Returns:
            Decision: Allow when ``state.test_mode`` is truthy, otherwise Block.

        Raises:
            ValueError: If invoked outside test mode.

        Example:
            >>> decision, message = guard._handle_reset_plan_review()  # doctest: +SKIP
        """
        if self.state.get("test_mode"):
            return "allow", "Test-mode reset allowed"
        raise ValueError("'/reset-plan-review' is only available in test mode.")

    # ── Transition validation ─────────────────────────────────────

    def _check_not_auto_phase(self) -> None:
        """
        Reject explicit invocation of an auto-phase.

        Auto-phases are entered automatically when the previous phase
        completes; invoking them as skills would cause a double-enter.

        Raises:
            ValueError: If ``self.next_phase`` is an auto-phase.

        Example:
            >>> # Raises ValueError when the next phase is an auto-phase:
            >>> guard._check_not_auto_phase()  # doctest: +SKIP
        """
        if self.config.is_auto_phase(self.next_phase):
            raise ValueError(
                f"'{self.next_phase}' is an auto-phase — it starts automatically after the previous phase completes. "
                f"Do not invoke it as a skill."
            )

    def _check_current_phase_done(self) -> None:
        """
        Forbid leaving the current phase before its status is ``completed`` or ``skipped``.

        Raises:
            ValueError: If transitioning while the current phase is not
                completed or skipped (with a friendlier message when the
                user is re-invoking the same phase).

        Example:
            >>> # Raises ValueError when leaving an unfinished phase:
            >>> guard._check_current_phase_done()  # doctest: +SKIP
        """
        if self.next_phase and self.status not in DONE_STATUSES:
            if self.next_phase == self.current:
                raise ValueError(
                    f"Already in '{self.current}' phase. Complete the phase tasks instead of re-invoking the skill."
                )
            raise ValueError(
                f"Phase '{self.current}' is not completed. Finish it before transitioning to '{self.next_phase}'."
            )

    def _resolve_prev_for_ordering(self) -> str | None:
        """
        Map an auto-phase ``current`` back to its preceding skill phase.

        Skill ordering is computed against the skill-phase list (auto-phases
        excluded). When the current phase is itself an auto-phase, this helper
        walks backwards through finished phases to find the last skill phase
        — that's the right "previous" anchor for the next-skill ordering check.
        If no skill phase precedes the current auto-phase (e.g. clarify is
        the very first phase, with nothing before it), returns ``None`` so
        the caller treats the next skill as the workflow's first.

        Returns:
            str | None: The skill-phase to use as ``prev``, or ``None`` if
            no prior skill phase exists.

        Example:
            >>> prev = guard._resolve_prev_for_ordering()  # doctest: +SKIP
        """
        skill_phases = [p for p in self.phases if not self.config.is_auto_phase(p)]
        if not self.config.is_auto_phase(self.current):
            return self.current
        finished = self.state.done_phase_names()
        for p in reversed(finished):
            if p in skill_phases:
                return p
        return None

    def _get_skill_phases(self) -> list[str]:
        """
        Return the ordered skill-only phase list, with TDD-only phases filtered.

        When ``state.tdd`` is False, the test-review phases are dropped so
        non-TDD workflows don't trip on a "you skipped test-review" error.

        Returns:
            list[str]: Skill-invokable phases in workflow order.

        Example:
            >>> skill_phases = guard._get_skill_phases()  # doctest: +SKIP
        """
        skill_phases = [p for p in self.phases if not self.config.is_auto_phase(p)]
        if not self.state.get("tdd", False):
            skill_phases = [
                p for p in skill_phases if p not in ("test-review", "tests-review")
            ]
        return skill_phases

    # ── Validate ──────────────────────────────────────────────────

    def _check_clarify_iteration_ceiling(self) -> Decision:
        """
        Enforce the ``clarify.max_iterations`` cap on AskUserQuestion calls.

        Returns:
            Decision: Block when the cap has been reached, allow otherwise.

        Example:
            >>> decision, message = guard._check_clarify_iteration_ceiling()  # doctest: +SKIP
        """
        if self.current != "clarify":
            return "allow", "AskUserQuestion allowed"
        phase = self.state.get_clarify_phase() or {}
        count = int(phase.get("iteration_count", 0))
        cap = self.config.clarify_max_iterations
        if count >= cap:
            return (
                "block",
                f"Max clarify iterations ({cap}) reached — please simplify the prompt and re-run /build",
            )
        return "allow", f"AskUserQuestion allowed in clarify ({count}/{cap})"

    def validate(self) -> Decision:
        """
        Validate the requested skill / phase transition.

        Dispatches to a special-skill handler if the next phase is one of the
        operator commands (``continue`` / ``plan-approved`` / ``revise-plan`` /
        ``reset-plan-review``). Otherwise enforces auto-phase, current-phase-done,
        and ordering checks against the workflow's skill-phase list. The
        Explore+Research parallel case is short-circuited.

        AskUserQuestion is also routed here so the clarify-phase iteration
        ceiling can be enforced without a separate guard module.

        Returns:
            Decision: ``("allow", message)`` if the transition is legal,
            otherwise ``("block", reason)``.

        Example:
            >>> decision, message = guard.validate()  # doctest: +SKIP
            >>> decision  # doctest: +SKIP
            'allow'
        """
        if self.tool_name == "AskUserQuestion":
            return self._check_clarify_iteration_ceiling()
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
