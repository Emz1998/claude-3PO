"""Report guard — blocks stop if report was not written.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads session state and checks validation.report_written == true.
"""

import sys
from pathlib import Path
import json
import subprocess
import re
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from workflow.headless_claude.claude import run_claude, load_prompt_template
from workflow.constants.config import (
    CONFIDENCE_SCORE_THRESHOLD,
    QUALITY_SCORE_THRESHOLD,
    MAX_ITERATIONS,
)

_SESSIONS_DIR = Path(__file__).resolve().parents[3] / "sessions"


def resolve_score_pattern(score_name: str) -> str:
    return rf"(?i)\b(?:the\s+|a\s+)?(?:{score_name})\s+score\s*(?:[:=]|is)\s*(100(?:\.0+)?\s*%?|[0-9]{1,2}(?:\.\d+)?\s*%?)\b"


def validate_score_exists(report_text: str) -> tuple[bool, str]:
    if (
        extract_score("confidence", report_text) is None
        and extract_score("quality", report_text) is None
    ):
        return (
            False,
            "Confidence and quality scores are missing. Please add confidence and quality scores to the report.",
        )
    if extract_score("confidence", report_text) is None:
        return (
            False,
            "Confidence score is missing. Please add confidence score to the report.",
        )
    if extract_score("quality", report_text) is None:
        return (
            False,
            "Quality score is missing. Please add quality score to the report.",
        )
    return True, "Scores are present in the report."


def extract_score(
    score_name: Literal["confidence", "quality"], report_text: str
) -> int | None:
    if score_name not in ["confidence", "quality"]:
        raise ValueError(f"Invalid score name: {score_name}")
    pattern = resolve_score_pattern(score_name)
    match = re.search(pattern, report_text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def validate_report_file_path(
    received_file_path: str, expected_file_path: str
) -> tuple[bool, str]:
    if expected_file_path != received_file_path:
        return (
            False,
            f"The file path is not the expected file path. Please write or edit the report in the expected file path: {expected_file_path}",
        )
    return True, f"File path is valid: {expected_file_path}"


def validate_score(score_name: str, score: str | int | None) -> tuple[bool, str]:

    if score is None:
        return (
            False,
            f"{score_name} score is missing. Please add {score_name} to the frontmatter.",
        )

    if not isinstance(score, int):
        return (
            False,
            f"{score_name} score must be an integer. Please change {score_name} to an integer in the frontmatter.",
        )

    if score not in range(0, 101):
        return (
            False,
            f"{score_name} score must be between 0 and 100.",
        )

    return True, f"{score_name} score is valid."


def validate_report(
    confidence_score: int | None, quality_score: int | None
) -> tuple[bool, str]:

    validations = [
        validate_score("confidence_score", confidence_score),
        validate_score("quality_score", quality_score),
    ]

    errors = [message for valid, message in validations if not valid]
    if errors:
        return False, "\n".join(errors)

    return True, "Report is valid."


def validate_need_iteration(
    confidence_score: int | None, quality_score: int | None
) -> bool:
    if confidence_score is None or quality_score is None:
        return False
    if (
        confidence_score < CONFIDENCE_SCORE_THRESHOLD
        or quality_score < QUALITY_SCORE_THRESHOLD
    ):
        return True
    return False


def review(
    prompt: str,
    session_id: str | None = None,
    _depth: int = 0,
) -> str:

    response = run_claude(prompt, session_id)
    claude_session_id = response.get("session_id")
    report_text = response.get("result", "")

    confidence_score = extract_score("confidence", report_text)
    quality_score = extract_score("quality", report_text)

    valid_report, message = validate_report(confidence_score, quality_score)
    if not valid_report:
        return review(message, claude_session_id, _depth + 1)

    return report_text
