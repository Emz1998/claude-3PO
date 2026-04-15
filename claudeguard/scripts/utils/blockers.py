"""blockers.py — Remaining check functions shared across validators.

Score/verdict validation and review section checks.
"""

from typing import Literal, Callable, cast

from .state_store import StateStore
from .extractors import extract_md_sections


Result = tuple[bool, str]


# ═══════════════════════════════════════════════════════════════════
# Score / verdict
# ═══════════════════════════════════════════════════════════════════


def check_score_present(confidence: int | None, quality: int | None) -> None:
    if confidence is None or quality is None:
        raise ValueError("Confidence and quality scores are required")


def check_score_range(confidence: int, quality: int) -> None:
    if confidence not in range(1, 101):
        raise ValueError("Confidence score must be between 1 and 100")
    if quality not in range(1, 101):
        raise ValueError("Quality score must be between 1 and 100")


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

    check_score_present(confidence, quality)
    check_score_range(confidence, quality)  # type: ignore[arg-type]

    return True, cast(dict[Literal["confidence_score", "quality_score"], int], scores)


def verdict_valid(
    content: str,
    extractor: Callable[[str], str],
) -> tuple[bool, Literal["Pass", "Fail"]]:
    """Validate that extracted verdict is Pass or Fail."""

    verdict = extractor(content)
    if verdict not in ["Pass", "Fail"]:
        raise ValueError("Verdict must be either 'Pass' or 'Fail'")

    return True, cast(Literal["Pass", "Fail"], verdict)


SCORE_PHASES = ["plan-review", "code-review"]
VERDICT_PHASES = ["test-review", "tests-review", "quality-check", "validate"]


def _check_report_not_empty(content: str) -> None:
    if not content:
        raise ValueError("Agent report is empty")


def _check_phase_requires_report(phase: str) -> None:
    if phase not in SCORE_PHASES and phase not in VERDICT_PHASES:
        raise ValueError(f"Phase '{phase}' does not require an agent report")


def is_agent_report_valid(
    hook_input: dict,
    state: StateStore,
    score_extractor: Callable[
        [str], dict[Literal["confidence_score", "quality_score"], int | None]
    ],
    verdict_extractor: Callable[[str], str],
) -> Result:
    """Validate the agent's report based on current phase."""
    phase = state.current_phase
    content = hook_input.get("last_assistant_message", "")

    _check_report_not_empty(content)
    _check_phase_requires_report(phase)

    if phase in SCORE_PHASES:
        scores_valid(content, score_extractor)
        return True, f"Agent report valid for {phase}: scores present"

    verdict_valid(content, verdict_extractor)
    return True, f"Agent report valid for {phase}: verdict present"


# ═══════════════════════════════════════════════════════════════════
# Review sections
# ═══════════════════════════════════════════════════════════════════


def _extract_bullet_items(content: str) -> list[str]:
    """Extract bullet list items (- item) from markdown content."""
    return [
        line.lstrip("- ").strip()
        for line in content.splitlines()
        if line.strip().startswith("- ")
    ]


def _require_section(sections: dict[str, str], heading: str) -> list[str]:
    """Require a section exists and has bullet items. Returns the items."""
    if heading not in sections:
        raise ValueError(f"'{heading}' section is required")
    items = _extract_bullet_items(sections[heading])
    if not items:
        raise ValueError(f"'{heading}' section is empty — provide file paths")
    return items


def validate_review_sections(content: str, phase: str) -> tuple[list[str], list[str]]:
    """Validate required sections in reviewer response.

    Returns (files_to_revise, tests_to_revise).
    - code-review: requires both "Files to revise" and "Tests to revise"
    - test-review: requires "Files to revise"
    - plan-review: no sections required
    """
    raw_sections = extract_md_sections(content, 2)
    sections = {heading: body for heading, body in raw_sections}

    if phase == "code-review":
        files = _require_section(sections, "Files to revise")
        tests = _require_section(sections, "Tests to revise")
        return files, tests

    if phase in ("test-review", "tests-review"):
        files = _require_section(sections, "Files to revise")
        return files, []

    return [], []
