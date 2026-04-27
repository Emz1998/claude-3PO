"""PhaseGuard — validates phase transitions triggered by Skill invocations.

**Pure validator** — never mutates state and never calls the resolver. Each
``handle_*`` method only returns a Decision describing whether the transition
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
    - **Special skill** — ``/continue`` is the universal advancer; it
      force-completes the current phase (or advances past an already-completed
      one) and lets the resolver auto-start the next phase.

    The class is a **pure validator** — handlers never mutate state. After
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
        self.phases = self.get_workflow_phases()

    def get_workflow_phases(self) -> list[str]:
        """Return the phase list for the current workflow type.

        Example:
            >>> phases = guard.get_workflow_phases()  # doctest: +SKIP
        """
        workflow_type = self.state.get("workflow_type", "implement")
        phases = self.config.get_phases(workflow_type)
        return phases if phases else self.config.main_phases

    # ── Ordering (absorbed from former lib/ordering.py) ──────────

    @staticmethod
    def validate_order(prev: str | None, next_item: str, order: list[str]) -> str:
        """
        Enforce strict forward-by-one ordering of items against ``order``.

        Used for both phase ordering (with current-phase as ``prev``) and
        skill ordering. The first transition (``prev is None``) must hit
        ``order[0]``; subsequent transitions must advance by exactly one
        position — equal index means "already entered", lower index means
        "going backwards", higher than +1 means "skipping items".

        Args:
            prev (str | None): Previous item, or ``None`` for the first
                transition.
            next_item (str): Item being transitioned to.
            order (list[str]): Reference order.

        Returns:
            str: Success message describing the allowed transition.

        Raises:
            ValueError: If the transition violates the ordering invariants.

        Example:
            >>> PhaseGuard.validate_order(None, "plan", ["plan", "code"])
            "Allowed to start with 'plan'"
            >>> PhaseGuard.validate_order("plan", "code", ["plan", "code"])
            "Phase is allowed to transition to 'code'"
        """
        # Next must exist in order before any index math runs.
        if next_item not in order:
            raise ValueError(f"Invalid next item '{next_item}'")

        # First transition has no prev — force callers to hit the canonical start.
        if prev is None:
            if next_item != order[0]:
                raise ValueError(f"Must start with '{order[0]}', not '{next_item}'")
            return f"Allowed to start with '{order[0]}'"

        if prev not in order:
            raise ValueError(f"Invalid previous item '{prev}'")

        prev_idx = order.index(prev)
        next_idx = order.index(next_item)

        # Three distinct error messages so the caller can tell whether the user
        # is re-invoking, going backwards, or skipping ahead.
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

    # ── Skill handlers ────────────────────────────────────────────

    def handle_continue(self) -> Decision:
        """
        Validate ``/continue`` — advance past the current phase.

        Pure: returns a Decision; the dispatcher is responsible for the
        actual phase advance via Recorder.

        Returns:
            Decision: Allow if the phase is completed or in_progress (which
            counts as a force-complete).

        Raises:
            ValueError: When the current phase has no advance-able status.

        Example:
            >>> decision, message = guard.handle_continue()  # doctest: +SKIP
        """
        if self.status == "completed":
            return "allow", f"Continuing after completed phase: {self.current}"
        if self.status == "in_progress":
            return "allow", f"Force-completed phase: {self.current}"
        raise ValueError(
            f"'/continue' cannot continue — current phase '{self.current}' has status '{self.status}'."
        )

    # ── Transition validation ─────────────────────────────────────

    def check_not_auto_phase(self) -> None:
        """
        Reject explicit invocation of an auto-phase.

        Auto-phases are entered automatically when the previous phase
        completes; invoking them as skills would cause a double-enter.

        Raises:
            ValueError: If ``self.next_phase`` is an auto-phase.

        Example:
            >>> # Raises ValueError when the next phase is an auto-phase:
            >>> guard.check_not_auto_phase()  # doctest: +SKIP
        """
        if self.config.is_auto_phase(self.next_phase):
            raise ValueError(
                f"'{self.next_phase}' is an auto-phase — it starts automatically after the previous phase completes. "
                f"Do not invoke it as a skill."
            )

    def check_current_phase_done(self) -> None:
        """
        Forbid leaving the current phase before its status is ``completed`` or ``skipped``.

        Raises:
            ValueError: If transitioning while the current phase is not
                completed or skipped (with a friendlier message when the
                user is re-invoking the same phase).

        Example:
            >>> # Raises ValueError when leaving an unfinished phase:
            >>> guard.check_current_phase_done()  # doctest: +SKIP
        """
        if self.next_phase and self.status not in DONE_STATUSES:
            # Same-phase re-invocation gets a bespoke hint; other cases share
            # the generic "finish current before moving" error.
            if self.next_phase == self.current:
                raise ValueError(
                    f"Already in '{self.current}' phase. Complete the phase tasks instead of re-invoking the skill."
                )
            raise ValueError(
                f"Phase '{self.current}' is not completed. Finish it before transitioning to '{self.next_phase}'."
            )

    def resolve_prev_for_ordering(self) -> str | None:
        """
        Map an auto-phase ``current`` back to its preceding skill phase.

        Skill ordering is computed against the skill-phase list (auto-phases
        excluded). When the current phase is itself an auto-phase, this helper
        walks backwards through finished phases to find the last skill phase
        — that's the right "previous" anchor for the next-skill ordering check.
        If no skill phase precedes the current auto-phase, returns ``None`` so
        the caller treats the next skill as the workflow's first.

        Returns:
            str | None: The skill-phase to use as ``prev``, or ``None`` if
            no prior skill phase exists.

        Example:
            >>> prev = guard.resolve_prev_for_ordering()  # doctest: +SKIP
        """
        skill_phases = [p for p in self.phases if not self.config.is_auto_phase(p)]
        if not self.config.is_auto_phase(self.current):
            return self.current
        # Walk backwards through finished phases so the last *skill* phase wins
        # as the ordering anchor — auto-phases aren't part of the skill order.
        finished = self.state.done_phase_names()
        for p in reversed(finished):
            if p in skill_phases:
                return p
        return None

    def get_skill_phases(self) -> list[str]:
        """
        Return the ordered skill-only phase list (auto-phases excluded).

        Returns:
            list[str]: Skill-invokable phases in workflow order.

        Example:
            >>> skill_phases = guard.get_skill_phases()  # doctest: +SKIP
        """
        return [p for p in self.phases if not self.config.is_auto_phase(p)]

    # ── Validate ──────────────────────────────────────────────────

    def validate(self) -> Decision:
        """
        Validate the requested skill / phase transition.

        Dispatches to :meth:`handle_continue` for the operator's universal
        ``/continue`` advancer. Otherwise enforces auto-phase, current-phase-done,
        and ordering checks against the workflow's skill-phase list. The
        Explore+Research parallel case is short-circuited.

        Returns:
            Decision: ``("allow", message)`` if the transition is legal,
            otherwise ``("block", reason)``.

        Example:
            >>> decision, message = guard.validate()  # doctest: +SKIP
            >>> decision  # doctest: +SKIP
            'allow'
        """
        try:
            # Operator skill bypasses the ordering check — handler enforces
            # its own phase/status preconditions.
            if self.next_phase == "continue":
                return self.handle_continue()

            self.check_not_auto_phase()

            # First-phase path: no `current` yet, so ordering check runs with prev=None.
            if not self.current:
                message = self.validate_order(None, self.next_phase, self.phases)
                return "allow", message

            # Parallel explore+research is allowed: Research launches alongside
            # an in-progress Explore without completing it first.
            if (
                self.current == "explore"
                and self.status == "in_progress"
                and self.next_phase == "research"
            ):
                return "allow", "Running Research in parallel with Explore"

            self.check_current_phase_done()

            skill_phases = self.get_skill_phases()
            prev = self.resolve_prev_for_ordering()
            message = self.validate_order(prev, self.next_phase, skill_phases)
            return "allow", message
        except ValueError as e:
            return "block", str(e)
