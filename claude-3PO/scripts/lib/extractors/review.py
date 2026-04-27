"""review.py — Extract reviewer scores and Pass/Fail verdicts from report text.

Reviewers may state intermediate scores while reasoning, so score parsing
always takes the *last* match; verdict parsing requires the verdict on the
final non-empty line and fail-closes on anything but ``"Pass"``.
"""

import re
from typing import Literal

from constants import SCORE_PATTERNS


def _extract_last_score(text: str, label: str) -> int | None:
    """Find the last labeled score (e.g. ``Confidence: 85``) in *text*; ``None`` if missing.

    Example:
        >>> _extract_last_score("Confidence: 70 then Confidence: 90", "confidence")
        90
        >>> _extract_last_score("nothing here", "confidence") is None
        True
    """
    matches: list[str] = []
    for pattern in SCORE_PATTERNS:
        matches.extend(re.findall(pattern.format(label=label), text, re.IGNORECASE))
    return int(matches[-1]) if matches else None


def extract_scores(
    text: str,
) -> dict[Literal["confidence_score", "quality_score"], int | None]:
    """
    Extract the latest confidence and quality scores from reviewer text.

    Reviewers may state intermediate scores while reasoning, so the *last*
    occurrence wins — that's the reviewer's final answer.

    Args:
        text (str): Free-form reviewer message body.

    Returns:
        dict[Literal["confidence_score", "quality_score"], int | None]: Both
        keys always present; values are ``None`` when no score was found.

    Example:
        >>> extract_scores("Confidence: 85\\nQuality: 90")
        {'confidence_score': 85, 'quality_score': 90}
    """
    return {
        "confidence_score": _extract_last_score(text, "confidence"),
        "quality_score": _extract_last_score(text, "quality"),
    }


def extract_verdict(message: str) -> str:
    """
    Extract a Pass/Fail verdict from the last non-empty line of *message*.

    Reviewers are required to put their final verdict on the last line. Anything
    that isn't exactly ``"Pass"`` is treated as a failure (fail-closed) so an
    ambiguous or malformed verdict can't accidentally let work through.

    Args:
        message (str): Full reviewer message.

    Returns:
        str: ``"Pass"`` or ``"Fail"``.

    Example:
        >>> extract_verdict("Looks good.\\nPass")
        'Pass'
        >>> extract_verdict("Needs work.\\nReject")
        'Fail'
    """
    lines = [line.strip() for line in message.strip().splitlines() if line.strip()]
    if not lines:
        return "Fail"
    last = lines[-1]
    if last == "Pass":
        return "Pass"
    return "Fail"
