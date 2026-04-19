"""specs_validation.py — Pure validators for architecture and backlog specs.

Extracted from ``utils/specs_writer.py`` so guardrails can validate report
content without importing the heavier ``utils/`` package (which also handles
*writing* those reports). The split keeps guard scripts lean.
"""

from utils.validator import SpecsValidator
from config import Config


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
        f"❌ {phase} validation FAILED (attempt {attempt}/{max_attempts}).\n\n"
        f"Errors:\n{bullets}\n\n"
        f"To course-correct:\n"
        f"  1. Read the template: {template}\n"
        f"  2. Re-emit the ENTIRE document with every required section + filled metadata (not a diff, not a summary).\n"
        f"  3. Minimal valid reference: {minimal}\n\n"
        f"{remaining} attempt(s) remaining. After {max_attempts} rejections the agent is marked failed "
        "and the workflow halts so the operator can intervene."
    )


def _validator() -> SpecsValidator:
    """Construct a ``SpecsValidator`` bound to the default ``Config()``.

    Example:
        >>> _validator()  # doctest: +SKIP
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
