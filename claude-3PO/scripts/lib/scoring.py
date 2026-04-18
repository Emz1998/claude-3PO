"""scoring.py — Pure validators for review scores and Pass/Fail verdicts.

Used by ``AgentReportGuard`` (validate-then-block) and the recorder
(extract-and-store). Lives in ``lib/`` so guard scripts don't pull in the
heavier ``utils/`` package just to validate a couple of integers.
"""

from typing import Callable, Literal, cast


ScoreDict = dict[Literal["confidence_score", "quality_score"], int]


def _check_score_present(confidence: int | None, quality: int | None) -> None:
    """Raise ``ValueError`` when either score is missing.

    Example:
        >>> _check_score_present(80, 90)  # returns None
    """
    if confidence is None or quality is None:
        raise ValueError("Confidence and quality scores are required")


def _check_score_range(confidence: int, quality: int) -> None:
    """Raise ``ValueError`` when either score is outside 1-100.

    Example:
        >>> _check_score_range(80, 90)  # returns None
    """
    if confidence not in range(1, 101):
        raise ValueError("Confidence score must be between 1 and 100")
    if quality not in range(1, 101):
        raise ValueError("Quality score must be between 1 and 100")


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
    confidence = scores["confidence_score"]
    quality = scores["quality_score"]
    _check_score_present(confidence, quality)
    _check_score_range(confidence, quality)  # type: ignore[arg-type]
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
