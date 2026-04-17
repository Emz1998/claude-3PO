"""AgentReportGuard — Validates agent reports at SubagentStop.

Validates content first (scores/verdict + required sections),
then records everything and resolves. If content is invalid,
blocks immediately — nothing gets recorded.
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
    """Validate agent report content (pure validator — no state mutation)."""

    SCORE_PHASES = ("plan-review", "code-review")
    VERDICT_PHASES = ("test-review", "tests-review", "quality-check", "validate")
    SPECS_PHASES = ("architect", "backlog")

    # Re-exported for back-compat with callers that still import from this class.
    scores_valid = staticmethod(scores_valid)
    verdict_valid = staticmethod(verdict_valid)

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
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
        if heading not in sections:
            raise ValueError(f"'{heading}' section is required")
        items = extract_bullet_items(sections[heading])
        if not items:
            raise ValueError(f"'{heading}' section is empty — provide file paths")
        return items

    @staticmethod
    def validate_review_sections(content: str, phase: str) -> tuple[list[str], list[str]]:
        """Validate required sections. Returns (files_to_revise, tests_to_revise)."""
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
        """Validate report structure. Returns success message."""
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
        """Validate architect or backlog report content."""
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
        """Build actionable stderr payload so the agent can actually course-correct."""
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
        """Returns ("allow", message) or ("block", reason).

        Pure validation — never mutates state. After Allow, dispatchers
        call Recorder/Resolver themselves. Review files/tests are exposed
        on ``self.review_files`` / ``self.review_tests`` for the dispatcher.
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
