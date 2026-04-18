"""specs_validation.py — Pure validators for architecture and backlog specs.

Extracted from ``utils/specs_writer.py`` so guardrails can validate report
content without importing the heavier ``utils/`` package (which also handles
*writing* those reports). The split keeps guard scripts lean.
"""

from utils.validator import SpecsValidator
from config import Config


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
