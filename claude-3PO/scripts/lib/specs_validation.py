"""Pure specs report validators.

Extracted from utils/specs_writer.py so guardrails can validate report
content without importing utils/* (writing those reports stays in utils/).
"""

from utils.validator import SpecsValidator
from config import Config


def _validator() -> SpecsValidator:
    return SpecsValidator(Config())


def validate_architecture_content(content: str) -> list[str]:
    """Validate architecture markdown content. Returns error list."""
    return _validator().validate_architecture(content)


def validate_backlog_content(content: str) -> list[str]:
    """Validate backlog markdown content. Returns error list."""
    return _validator().validate_backlog_md(content)
