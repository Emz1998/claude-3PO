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
    extract_bullet_items,
)
from lib.scoring import scores_valid, verdict_valid
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
      :meth:`format_rejection_message`.

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

    @staticmethod
    def _require_section(sections: dict[str, str], heading: str) -> list[str]:
        """
        Return non-empty bullet items from a required H2 section, or raise.

        Args:
            sections (dict[str, str]): Section-map produced by
                :func:`lib.extractors.extract_section_map`.
            heading (str): Required H2 heading text.

        Returns:
            list[str]: Bullet items found under the heading.

        Raises:
            ValueError: If the section is missing or contains no bullet items.

        Example:
            >>> AgentReportGuard._require_section({"Files to revise": "- a.py"}, "Files to revise")
            ['a.py']
        """
        if heading not in sections:
            raise ValueError(f"'{heading}' section is required")
        items = extract_bullet_items(sections[heading])
        if not items:
            raise ValueError(f"'{heading}' section is empty — provide file paths")
        return items

    @staticmethod
    def validate_review_sections(content: str, phase: str) -> tuple[list[str], list[str]]:
        """
        Extract the ``Files to revise`` / ``Tests to revise`` lists for review phases.

        Args:
            content (str): Raw markdown report body.
            phase (str): Current phase name. Only the review phases produce
                lists; all others return ``([], [])``.

        Returns:
            tuple[list[str], list[str]]: ``(files_to_revise, tests_to_revise)``.
            ``tests_to_revise`` is empty for test-review phases (the test files
            themselves are the ones being revised).

        Raises:
            ValueError: If a required section is missing or empty (propagated
                from :meth:`_require_section`).

        Example:
            >>> AgentReportGuard.validate_review_sections("# Report", "explore")
            ([], [])
        """
        sections = extract_section_map(content, 2)

        if phase == "code-review":
            files = AgentReportGuard._require_section(sections, "Files to revise")
            tests = AgentReportGuard._require_section(sections, "Tests to revise")
            return files, tests

        if phase in ("test-review", "tests-review"):
            files = AgentReportGuard._require_section(sections, "Files to revise")
            return files, []

        return [], []

    # ── Report validation ─────────────────────────────────────────

    def _validate_report(self) -> str:
        """
        Dispatch to the per-phase-class validator and return a success message.

        Returns:
            str: Phase-specific success message describing what passed.

        Raises:
            ValueError: If the report is empty, the phase doesn't require a
                report, or the phase-specific structural check fails.

        Example:
            >>> message = guard._validate_report()  # doctest: +SKIP
        """
        if not self.content:
            raise ValueError("Agent report is empty")

        all_phases = self.SCORE_PHASES + self.VERDICT_PHASES + self.SPECS_PHASES
        if self.phase not in all_phases:
            raise ValueError(f"Phase '{self.phase}' does not require an agent report")

        if self.phase in self.SCORE_PHASES:
            self.scores_valid(self.content, extract_scores)
            return f"Agent report valid for {self.phase}: scores present"

        if self.phase in self.VERDICT_PHASES:
            self.verdict_valid(self.content, extract_verdict)
            return f"Agent report valid for {self.phase}: verdict present"

        return self._validate_specs_report()

    def _validate_specs_report(self) -> str:
        """
        Validate an architecture / backlog report against template-derived schemas.

        Errors from ``lib.specs_validation`` are stored on ``self.errors`` so
        dispatchers can build a rich rejection message via
        :meth:`format_rejection_message`.

        Returns:
            str: Success message indicating which spec passed.

        Raises:
            ValueError: With the first validation error as its message; the
                full list lives on ``self.errors``.

        Example:
            >>> message = guard._validate_specs_report()  # doctest: +SKIP
        """
        from lib.specs_validation import (
            validate_architecture_content,
            validate_backlog_content,
        )

        if self.phase == "architect":
            errors = validate_architecture_content(self.content)
            if errors:
                self.errors = errors
                raise ValueError(f"Architecture validation: {errors[0]}")
            return "Agent report valid for architect: structure verified"

        errors = validate_backlog_content(self.content)
        if errors:
            self.errors = errors
            raise ValueError(f"Backlog validation: {errors[0]}")
        return "Agent report valid for backlog: structure verified"

    def _validate_sections(self) -> tuple[list[str], list[str]]:
        """Wrap :meth:`validate_review_sections` with this instance's content/phase.

        Example:
            >>> files, tests = guard._validate_sections()  # doctest: +SKIP
        """
        return self.validate_review_sections(self.content, self.phase)

    SPECS_AGENT_BY_PHASE = {"architect": "Architect", "backlog": "ProductOwner"}

    _TEMPLATE_HINTS = {
        "architect": (
            "${CLAUDE_PLUGIN_ROOT}/templates/architecture.md",
            "${CLAUDE_PLUGIN_ROOT}/templates/test/minimal-architecture.md",
        ),
        "backlog": (
            "${CLAUDE_PLUGIN_ROOT}/templates/backlog.md",
            "${CLAUDE_PLUGIN_ROOT}/templates/test/minimal-backlog.md",
        ),
    }

    @staticmethod
    def format_rejection_message(
        phase: str,
        errors: list[str],
        attempt: int,
        max_attempts: int,
    ) -> str:
        """
        Build an actionable stderr payload so the agent can course-correct.

        The message includes the full error list, the canonical + minimal
        template paths for the phase, and the remaining-attempts count so the
        agent knows how many tries it has before the workflow halts.

        Args:
            phase (str): Spec phase name (``architect`` or ``backlog``).
            errors (list[str]): Structural validation errors.
            attempt (int): The 1-based attempt number that just failed.
            max_attempts (int): Maximum allowed attempts before halt.

        Returns:
            str: Formatted multi-line stderr payload.

        Example:
            >>> msg = AgentReportGuard.format_rejection_message(
            ...     "architect", ["missing section: Overview"], 1, 3
            ... )
            >>> "Re-emit the ENTIRE document" in msg
            True
        """
        template, minimal = AgentReportGuard._TEMPLATE_HINTS.get(
            phase, ("(no template)", "(no minimal reference)")
        )
        bullets = "\n".join(f"  - {e}" for e in errors)
        remaining = max(0, max_attempts - attempt)
        return (
            f"❌ {phase} validation FAILED (attempt {attempt}/{max_attempts}).\n\n"
            f"Errors:\n{bullets}\n\n"
            f"To course-correct:\n"
            f"  1. Read the template: {template}\n"
            f"  2. Re-emit the ENTIRE document with every required section + filled metadata (not a diff, not a summary).\n"
            f"  3. Minimal valid reference: {minimal}\n\n"
            f"{remaining} attempt(s) remaining. After {max_attempts} rejections the agent is marked failed "
            "and the workflow halts so the operator can intervene."
        )

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
            message = self._validate_report()

            if self.phase in self.SPECS_PHASES:
                return "allow", message

            files, tests = self._validate_sections()
            self.review_files, self.review_tests = files, tests

            return "allow", message
        except ValueError as e:
            if not self.errors:
                self.errors = [str(e)]
            return "block", str(e)
