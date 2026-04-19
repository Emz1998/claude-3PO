"""validators.py — Pure validators for review scores, verdicts, and specs docs.

Consolidates two previously separate validators:

* **Score / verdict** (``scores_valid``, ``verdict_valid``) — used by
  :class:`AgentReportGuard` (validate-then-block) and the recorder
  (extract-and-store) to check reviewer report content.
* **Specs content** (``validate_architecture_content``,
  ``validate_backlog_content``, ``format_rejection_message``) — thin wrappers
  over :class:`utils.validator.SpecsValidator` that let guardrails validate a
  specs report without pulling in the heavier ``utils/`` package directly.

Lives in ``lib/`` so guard scripts can validate without importing the heavier
``utils/`` package (which handles writing those reports too).
"""

from functools import lru_cache
from typing import Callable, Literal, cast

from utils.validator import SpecsValidator
from config import Config


# ---------------------------------------------------------------------------
# Score / verdict validation
# ---------------------------------------------------------------------------

ScoreDict = dict[Literal["confidence_score", "quality_score"], int]


def scores_valid(
    content: str,
    extractor: Callable[[str], dict[Literal["confidence_score", "quality_score"], int | None]],
) -> tuple[bool, ScoreDict]:
    """
    Validate that *extractor* finds both scores and that they're in 1-100.

    Takes the extractor as a callable rather than calling ``extract_scores``
    directly so the guard layer can swap parsing strategies (or inject a fake
    in tests) without touching this validator.

    Args:
        content (str): Reviewer message text.
        extractor (Callable): Function that pulls ``{confidence_score,
            quality_score}`` from *content*; values may be ``None``.

    Returns:
        tuple[bool, ScoreDict]: Always ``(True, scores)`` on success — failures
        raise rather than return ``False``, since callers of this validator
        either succeed or surface the error to the user.

    Raises:
        ValueError: When a score is missing or outside the 1-100 range.

    Example:
        >>> from lib.extractors import extract_scores
        >>> ok, scores = scores_valid("Confidence: 80\\nQuality: 90", extract_scores)
        >>> ok, scores["confidence_score"], scores["quality_score"]
        (True, 80, 90)
    """
    scores = extractor(content)
    confidence, quality = scores["confidence_score"], scores["quality_score"]
    if confidence is None or quality is None:
        raise ValueError("Confidence and quality scores are required")
    if confidence not in range(1, 101):
        raise ValueError("Confidence score must be between 1 and 100")
    if quality not in range(1, 101):
        raise ValueError("Quality score must be between 1 and 100")
    return True, cast(ScoreDict, scores)


def verdict_valid(
    content: str,
    extractor: Callable[[str], str],
) -> tuple[bool, Literal["Pass", "Fail"]]:
    """
    Validate that *extractor* yields exactly ``"Pass"`` or ``"Fail"``.

    Args:
        content (str): Reviewer message text.
        extractor (Callable[[str], str]): Function returning the verdict string.

    Returns:
        tuple[bool, Literal["Pass", "Fail"]]: Always ``(True, verdict)`` on success.

    Raises:
        ValueError: When the extracted verdict is anything other than
            ``"Pass"`` or ``"Fail"``.

    Example:
        >>> from lib.extractors import extract_verdict
        >>> verdict_valid("looks good\\nPass", extract_verdict)
        (True, 'Pass')
    """
    verdict = extractor(content)
    if verdict not in ("Pass", "Fail"):
        raise ValueError("Verdict must be either 'Pass' or 'Fail'")
    return True, cast(Literal["Pass", "Fail"], verdict)


# ---------------------------------------------------------------------------
# Specs content validation
# ---------------------------------------------------------------------------

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


def format_rejection_message(
    phase: str,
    errors: list[str],
    attempt: int,
    max_attempts: int,
) -> str:
    """
    Build an actionable stderr payload so a specs agent can course-correct.

    Bundles the full error list, canonical + minimal template paths, and the
    remaining-attempts count so the agent knows the cap before the workflow
    halts.

    Args:
        phase (str): Spec phase name (``architect`` or ``backlog``).
        errors (list[str]): Structural validation errors.
        attempt (int): The 1-based attempt number that just failed.
        max_attempts (int): Maximum allowed attempts before halt.

    Returns:
        str: Formatted multi-line stderr payload.

    Example:
        >>> msg = format_rejection_message(
        ...     "architect", ["missing section: Overview"], 1, 3
        ... )
        >>> "Re-emit the ENTIRE document" in msg
        True
    """
    # Fallback strings keep the payload readable when an unknown phase sneaks in —
    # never raises, because this runs on the error path.
    template, minimal = _TEMPLATE_HINTS.get(
        phase, ("(no template)", "(no minimal reference)")
    )
    bullets = "\n".join(f"  - {e}" for e in errors)
    remaining = max(0, max_attempts - attempt)
    return (
        f"[FAIL] {phase} validation FAILED (attempt {attempt}/{max_attempts}).\n\n"
        f"Errors:\n{bullets}\n\n"
        f"To course-correct:\n"
        f"  1. Read the template: {template}\n"
        f"  2. Re-emit the ENTIRE document with every required section + filled metadata (not a diff, not a summary).\n"
        f"  3. Minimal valid reference: {minimal}\n\n"
        f"{remaining} attempt(s) remaining. After {max_attempts} rejections the agent is marked failed "
        "and the workflow halts so the operator can intervene."
    )


@lru_cache(maxsize=1)
def _validator() -> SpecsValidator:
    """Return a process-cached ``SpecsValidator`` bound to ``Config()``.

    Cached because ``SpecsValidator``'s template-schema cache is per-instance —
    rebuilding on each call re-parses ``templates/architecture.md`` /
    ``templates/backlog.md`` from disk, which compounds on the PostToolUse hot
    path (one validation per architect/backlog Task finish).

    Returns:
        SpecsValidator: Singleton validator instance.

    Example:
        >>> _validator() is _validator()  # doctest: +SKIP
        True
    """
    return SpecsValidator(Config())


def validate_architecture_content(content: str) -> list[str]:
    """
    Validate architecture markdown against the template-derived schema.

    Args:
        content (str): Architecture markdown to validate.

    Returns:
        list[str]: Human-readable error messages, empty if validation passed.

    Example:
        >>> errors = validate_architecture_content("# bad doc")  # doctest: +SKIP
        >>> isinstance(errors, list)
        True
    """
    return _validator().validate_architecture(content)


def validate_backlog_content(content: str) -> list[str]:
    """
    Validate backlog markdown against the template-derived schema.

    Args:
        content (str): Backlog markdown to validate.

    Returns:
        list[str]: Human-readable error messages, empty if validation passed.

    Example:
        >>> errors = validate_backlog_content("# bad doc")  # doctest: +SKIP
        >>> isinstance(errors, list)
        True
    """
    return _validator().validate_backlog_md(content)
