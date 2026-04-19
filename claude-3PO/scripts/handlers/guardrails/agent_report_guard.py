"""AgentReportGuard — validates agent reports at SubagentStop (pure validator).

Validates report content (scores / verdict / spec structure + required review
sections). If content is invalid, returns Block immediately — no state mutation
happens here. After Allow, the dispatcher is responsible for invoking the
Recorder/Resolver with the data exposed on the guard's instance attributes.
"""

from typing import Literal

from lib.extractors import (
    extract_scores,
    extract_verdict,
    extract_section_map,
    require_section,
)
from lib.validators import scores_valid, verdict_valid
from lib.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class AgentReportGuard:
    """Validate an agent's stop-time report. **Pure validator — no state mutation.**

    The guard recently became a pure validator: it no longer calls Recorder /
    Resolver. Dispatchers are responsible for applying side effects after a
    successful Allow, using the data the guard exposes:

    - ``self.review_files`` / ``self.review_tests`` — file lists parsed from
      the review report (populated for ``code-review`` / ``test-review`` /
      ``tests-review`` phases).
    - ``self.errors`` — accumulated structural-validation errors (specs phases),
      so dispatchers can render rich rejection messages via
      :func:`lib.validators.format_rejection_message`.

    Phase classes:

    - ``SCORE_PHASES`` — require a numeric scores block (plan-review, code-review).
    - ``VERDICT_PHASES`` — require a Pass/Fail verdict (test-review/tests-review,
      quality-check, validate).
    - ``SPECS_PHASES`` — require a structurally valid architecture / backlog
      document, validated against the canonical templates.

    Example:
        >>> guard = AgentReportGuard(hook_input, config, state)  # doctest: +SKIP
        >>> decision, message = guard.validate()  # doctest: +SKIP
    """

    SCORE_PHASES = ("plan-review", "code-review")
    VERDICT_PHASES = ("test-review", "tests-review", "quality-check", "validate")
    SPECS_PHASES = ("architect", "backlog")

    SPECS_AGENT_BY_PHASE = {"architect": "Architect", "backlog": "ProductOwner"}

    # Re-exported for back-compat with callers that still import from this class.
    scores_valid = staticmethod(scores_valid)
    verdict_valid = staticmethod(verdict_valid)

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        """
        Cache hook payload and dependencies; initialise dispatcher-facing attrs.

        Args:
            hook_input (dict): Raw Stop-hook payload. ``last_assistant_message``
                is treated as the agent's report content.
            config (Config): Workflow configuration.
            state (StateStore): Mutable workflow state snapshot — read only.

        Example:
            >>> guard = AgentReportGuard(hook_input, config, state)  # doctest: +SKIP
            >>> guard.errors  # doctest: +SKIP
            []
        """
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.phase = state.current_phase
        self.content = hook_input.get("last_assistant_message", "")
        self.errors: list[str] = []
        self.review_files: list[str] = []
        self.review_tests: list[str] = []

    # ── Section validation ────────────────────────────────────────

    def validate_review_sections(self) -> None:
        """
        Populate ``review_files`` / ``review_tests`` from the review report body.

        Dispatchers read the populated attrs after Allow to drive the revision
        loop — they're on the instance (not returned) to keep ``validate()``
        linear and to give failures a stable target for rejection messages.

        Raises:
            ValueError: If a required section is missing or empty (propagated
                from :func:`lib.extractors.require_section`).

        Example:
            >>> guard.validate_review_sections()  # doctest: +SKIP
            >>> guard.review_files  # doctest: +SKIP
            ['src/app.py']

        SideEffect:
            Sets ``self.review_files`` and ``self.review_tests`` to the bullet
            items parsed from the corresponding H2 sections.
        """
        # Non-review phases (plan-review, quality-check, etc.) have no file
        # lists to parse — leave the attrs at their __init__ defaults ([]).
        sections = extract_section_map(self.content, 2)

        if self.phase == "code-review":
            self.review_files = require_section(sections, "Files to revise")
            self.review_tests = require_section(sections, "Tests to revise")
            return

        if self.phase in ("test-review", "tests-review"):
            # Test-review only revises test files — there's no separate
            # "Tests to revise" list because the files themselves are tests.
            self.review_files = require_section(sections, "Files to revise")

    # ── Report validation ─────────────────────────────────────────

    def validate_review_report(self) -> None:
        """
        Validate a scores/verdict review report and extract revision lists.

        Raises:
            ValueError: If the report is empty, the phase doesn't require a
                report, or the phase-specific structural check fails.

        Example:
            >>> guard.validate_review_report()  # doctest: +SKIP

        SideEffect:
            Via :meth:`validate_review_sections`, may set ``self.review_files``
            and ``self.review_tests``.
        """
        # Empty content fails first so the caller's block message is specific.
        if not self.content:
            raise ValueError("Agent report is empty")

        all_phases = self.SCORE_PHASES + self.VERDICT_PHASES + self.SPECS_PHASES
        if self.phase not in all_phases:
            raise ValueError(f"Phase '{self.phase}' does not require an agent report")

        # Phase-specific structural check runs first so scoring/verdict errors
        # surface before missing-section errors on the same report.
        if self.phase in self.SCORE_PHASES:
            self.scores_valid(self.content, extract_scores)

        if self.phase in self.VERDICT_PHASES:
            self.verdict_valid(self.content, extract_verdict)

        # Review-file extraction last — only relevant for code/test-review phases;
        # other phases skip inside validate_review_sections.
        self.validate_review_sections()

    def validate_specs_report(self) -> None:
        """
        Validate an architecture / backlog report against template-derived schemas.

        Errors from ``lib.validators`` are stored on ``self.errors`` so
        dispatchers can build a rich rejection message via
        :func:`lib.validators.format_rejection_message`.

        Raises:
            ValueError: With the first validation error as its message; the
                full list lives on ``self.errors``.

        Example:
            >>> guard.validate_specs_report()  # doctest: +SKIP

        SideEffect:
            On failure, sets ``self.errors`` to the full list of validator errors.
        """
        # Deferred import: validators pulls in utils.validator which
        # transitively imports heavier modules the hot path shouldn't pay for.
        from lib.validators import (
            validate_architecture_content,
            validate_backlog_content,
        )

        if not self.content:
            raise ValueError("Agent report is empty")

        if self.phase == "architect":
            errors = validate_architecture_content(self.content)
            if errors:
                self.errors = errors
                raise ValueError(f"Architecture validation: {errors[0]}")
            return

        errors = validate_backlog_content(self.content)
        if errors:
            self.errors = errors
            raise ValueError(f"Backlog validation: {errors[0]}")

    # ── Validate ──────────────────────────────────────────────────

    def validate(self) -> Decision:
        """
        Validate the report and return an allow/block decision.

        **Pure validation — never mutates state.** After Allow, the dispatcher is
        expected to apply side effects via Recorder/Resolver. Review files/tests
        parsed during section validation are exposed on ``self.review_files`` /
        ``self.review_tests`` for the dispatcher to consume.

        Returns:
            Decision: ``("allow", message)`` if the report is structurally
            valid, otherwise ``("block", reason)``. Block also seeds
            ``self.errors`` with the failure for downstream messaging.

        Example:
            >>> decision, message = guard.validate()  # doctest: +SKIP
            >>> decision  # doctest: +SKIP
            'allow'
        """
        try:
            # Specs phases have their own validator that bypasses the scores /
            # verdict / review-section path entirely.
            if self.phase in self.SPECS_PHASES:
                self.validate_specs_report()
                return "allow", f"Agent report valid for {self.phase}: structure verified"

            self.validate_review_report()
            return "allow", f"Agent report valid for {self.phase}"
        except ValueError as e:
            # Seed errors for the dispatcher if a sub-validator didn't already populate it.
            if not self.errors:
                self.errors = [str(e)]
            return "block", str(e)
