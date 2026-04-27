"""validators.py — Pure validators for review scores and verdicts.

* :func:`scores_valid` and :func:`verdict_valid` are used by
  :class:`AgentReportGuard` (validate-then-block) and the recorder
  (extract-and-store) to check reviewer report content.

Lives in ``lib/`` so guard scripts can validate without importing the
heavier ``utils/`` package.
"""

from lib.extractors.markdown import trees_identical, build_md_tree  # type: ignore
from pathlib import Path
from typing import Callable, Literal, cast

_DIFF_SEPARATOR = "\n\n------------------------------------\n\n"

# ---------------------------------------------------------------------------
# Score / verdict validation
# ---------------------------------------------------------------------------

ScoreDict = dict[Literal["confidence_score", "quality_score"], int]


def scores_valid(
    content: str,
    extractor: Callable[
        [str], dict[Literal["confidence_score", "quality_score"], int | None]
    ],
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


def template_conformance_check(actual_content: str, template: Path) -> tuple[bool, str]:
    """
    Build a ConformanceCheck that matches responses against *template*'s md tree.

    The returned callable reads *template* each invocation so callers can
    edit the template mid-session and pick up the new structure without
    rebuilding the check.

    Args:
        template (Path): Path to the markdown template file.

    Returns:
        ConformanceCheck: ``(response) -> (is_ok, stitched_diff_str)``.

    Raises:
        FileNotFoundError: When the check is *called* and *template* is missing.

    Example:
        >>> check = template_tree_check(Path("plan.md"))  # doctest: +SKIP
        >>> check("# Wrong")  # doctest: +SKIP
        (False, '...')
        Return: (False, '...')
    """

    template_tree = build_md_tree(template.read_text())
    response_tree = build_md_tree(actual_content)
    ok, diff = trees_identical(template_tree, response_tree)

    return ok, _DIFF_SEPARATOR.join(diff)


def scores_present(actual_content: str) -> tuple[bool, dict[str, str]]:
    """
    Check if the actual content contains scores.
    """

    lines = actual_content.splitlines()

    confidence_score = ""
    quality_score = ""

    for line in lines:
        if line.startswith("Confidence Score:"):
            confidence_score = line.split(":")[1].strip()
        if line.startswith("Quality Score:"):
            quality_score = line.split(":")[1].strip()

    if not confidence_score or not quality_score:
        return False, {}

    return True, {
        "confidence_score": confidence_score,
        "quality_score": quality_score,
    }


def verdict_present(actual_content: str) -> tuple[bool, str]:
    """
    Check if the actual content contains a verdict.
    """
    lines = actual_content.splitlines()
    verdict = ""
    for line in lines:
        if line.startswith("Verdict:"):
            verdict = line.split(":")[1].strip()

    if verdict not in ["Pass", "Fail"]:
        return False, ""

    return True, verdict
