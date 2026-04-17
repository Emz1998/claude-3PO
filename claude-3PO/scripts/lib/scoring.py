"""Pure validators for review scores and verdicts.

Used by AgentReportGuard (validate) and Recorder (extract for storage).
Lives in lib/ so guards do not need to import from utils/.
"""

from typing import Callable, Literal, cast


ScoreDict = dict[Literal["confidence_score", "quality_score"], int]


def _check_score_present(confidence: int | None, quality: int | None) -> None:
    if confidence is None or quality is None:
        raise ValueError("Confidence and quality scores are required")


def _check_score_range(confidence: int, quality: int) -> None:
    if confidence not in range(1, 101):
        raise ValueError("Confidence score must be between 1 and 100")
    if quality not in range(1, 101):
        raise ValueError("Quality score must be between 1 and 100")


def scores_valid(
    content: str,
    extractor: Callable[[str], dict[Literal["confidence_score", "quality_score"], int | None]],
) -> tuple[bool, ScoreDict]:
    """Validate extracted scores are present and in 1-100 range."""
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
    """Validate extracted verdict is 'Pass' or 'Fail'."""
    verdict = extractor(content)
    if verdict not in ("Pass", "Fail"):
        raise ValueError("Verdict must be either 'Pass' or 'Fail'")
    return True, cast(Literal["Pass", "Fail"], verdict)
