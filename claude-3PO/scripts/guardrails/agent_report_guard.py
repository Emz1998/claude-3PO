"""AgentReportGuard — Validates agent reports at SubagentStop.

Validates content first (scores/verdict + required sections),
then records everything and resolves. If content is invalid,
blocks immediately — nothing gets recorded.
"""

from typing import Literal, Callable, cast

from lib.extractors import extract_scores, extract_verdict, extract_md_sections
from utils.resolver import resolve
from lib.state_store import StateStore
from config import Config


Decision = tuple[Literal["allow", "block"], str]


class AgentReportGuard:
    """Validate agent report content and record results."""

    SCORE_PHASES = ("plan-review", "code-review")
    VERDICT_PHASES = ("test-review", "tests-review", "quality-check", "validate")

    def __init__(self, hook_input: dict, config: Config, state: StateStore):
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.phase = state.current_phase
        self.content = hook_input.get("last_assistant_message", "")

    # ── Score validation ──────────────────────────────────────────

    @staticmethod
    def _check_score_present(confidence: int | None, quality: int | None) -> None:
        if confidence is None or quality is None:
            raise ValueError("Confidence and quality scores are required")

    @staticmethod
    def _check_score_range(confidence: int, quality: int) -> None:
        if confidence not in range(1, 101):
            raise ValueError("Confidence score must be between 1 and 100")
        if quality not in range(1, 101):
            raise ValueError("Quality score must be between 1 and 100")

    @staticmethod
    def scores_valid(
        content: str,
        extractor: Callable[
            [str], dict[Literal["confidence_score", "quality_score"], int | None]
        ],
    ) -> tuple[bool, dict[Literal["confidence_score", "quality_score"], int]]:
        """Validate that extracted scores are present and in range (1-100)."""
        scores = extractor(content)
        confidence = scores["confidence_score"]
        quality = scores["quality_score"]
        AgentReportGuard._check_score_present(confidence, quality)
        AgentReportGuard._check_score_range(confidence, quality)  # type: ignore[arg-type]
        return True, cast(dict[Literal["confidence_score", "quality_score"], int], scores)

    # ── Verdict validation ────────────────────────────────────────

    @staticmethod
    def verdict_valid(
        content: str,
        extractor: Callable[[str], str],
    ) -> tuple[bool, Literal["Pass", "Fail"]]:
        """Validate that extracted verdict is Pass or Fail."""
        verdict = extractor(content)
        if verdict not in ["Pass", "Fail"]:
            raise ValueError("Verdict must be either 'Pass' or 'Fail'")
        return True, cast(Literal["Pass", "Fail"], verdict)

    # ── Section validation ────────────────────────────────────────

    @staticmethod
    def _extract_bullet_items(content: str) -> list[str]:
        return [
            line.lstrip("- ").strip()
            for line in content.splitlines()
            if line.strip().startswith("- ")
        ]

    @staticmethod
    def _require_section(sections: dict[str, str], heading: str) -> list[str]:
        if heading not in sections:
            raise ValueError(f"'{heading}' section is required")
        items = AgentReportGuard._extract_bullet_items(sections[heading])
        if not items:
            raise ValueError(f"'{heading}' section is empty — provide file paths")
        return items

    @staticmethod
    def validate_review_sections(content: str, phase: str) -> tuple[list[str], list[str]]:
        """Validate required sections. Returns (files_to_revise, tests_to_revise)."""
        raw_sections = extract_md_sections(content, 2)
        sections = {heading: body for heading, body in raw_sections}

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
        if self.phase not in self.SCORE_PHASES and self.phase not in self.VERDICT_PHASES:
            raise ValueError(f"Phase '{self.phase}' does not require an agent report")

        if self.phase in self.SCORE_PHASES:
            self.scores_valid(self.content, extract_scores)
            return f"Agent report valid for {self.phase}: scores present"

        self.verdict_valid(self.content, extract_verdict)
        return f"Agent report valid for {self.phase}: verdict present"

    def _validate_sections(self) -> tuple[list[str], list[str]]:
        return self.validate_review_sections(self.content, self.phase)

    # ── Validate ──────────────────────────────────────────────────

    def validate(self) -> Decision:
        """Returns ("allow", message) or ("block", reason)."""
        try:
            from utils.recorder import Recorder

            message = self._validate_report()
            files, tests = self._validate_sections()

            recorder = Recorder(self.state)
            recorder.record_scores(self.phase, self.content)
            recorder.record_verdict(self.phase, self.content)
            recorder.record_revision_files(self.phase, files, tests)

            resolve(self.config, self.state)

            return "allow", message
        except ValueError as e:
            return "block", str(e)
