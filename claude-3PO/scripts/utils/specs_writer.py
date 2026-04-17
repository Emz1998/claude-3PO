"""specs_writer.py — Writes specs docs (md + json for backlog) to disk.

Validates content before writing. Used by AgentReportGuard for
auto-writing architect and backlog outputs.
"""

import json
from pathlib import Path

from config import Config
from utils.validator import SpecsValidator


def _validator() -> SpecsValidator:
    return SpecsValidator(Config())


def write_doc(content: str, file_path: str) -> None:
    """Write markdown content to disk. Validates non-empty content and path."""
    if not content.strip():
        raise ValueError("Document content is empty")
    if not file_path:
        raise ValueError("File path is empty")
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_backlog(content: str, md_path: str, json_path: str) -> None:
    """Write backlog.md and convert to backlog.json."""
    if not content.strip():
        raise ValueError("Backlog content is empty")
    write_doc(content, md_path)
    data = _validator().convert_backlog_md_to_json(content)
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


from lib.specs_validation import (  # noqa: F401  (re-exports for back-compat)
    validate_architecture_content,
    validate_backlog_content,
)
