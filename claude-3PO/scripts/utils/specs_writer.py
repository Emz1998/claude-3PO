"""specs_writer.py — Writes specs docs (md + json for backlog) to disk.

Validates content before writing. Used by AgentReportGuard for
auto-writing architect and backlog outputs. The bottom of this module
re-exports two ``validate_*`` helpers from :mod:`lib.validators`
for back-compat — older guards imported them from here, and silently
breaking those import paths would be an upgrade hazard.
"""

import json
from pathlib import Path

from lib.validators import _validator


def write_doc(content: str, file_path: str) -> None:
    """Write markdown content to disk after light validation.

    Validates that both ``content`` and ``file_path`` are non-empty before
    touching the filesystem; both checks raise rather than silently no-op
    so a misconfigured caller fails loudly instead of producing an empty
    file with a wrong name. Parent directories are created on demand.

    Args:
        content (str): Markdown body to write (must be non-blank).
        file_path (str): Absolute filesystem path to write to.

    Raises:
        ValueError: If ``content`` is blank or ``file_path`` is empty.
        OSError: If the file cannot be written.

    Example:
        >>> write_doc("# Title", "/tmp/doc.md")  # doctest: +SKIP
    """
    if not content.strip():
        raise ValueError("Document content is empty")
    if not file_path:
        raise ValueError("File path is empty")
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_backlog(content: str, md_path: str, json_path: str) -> None:
    """Write backlog markdown to ``md_path`` and a derived JSON to ``json_path``.

    The markdown is the source of truth — the JSON is regenerated from
    it on every write via :meth:`SpecsValidator.convert_backlog_md_to_json`.
    That way the two files can never drift: writing the markdown is the
    only authoring action, and the JSON view stays consistent for
    downstream consumers (sprint planners, CI, etc).

    Args:
        content (str): Backlog markdown body (must be non-blank).
        md_path (str): Path for the markdown file.
        json_path (str): Path for the derived JSON file.

    Raises:
        ValueError: If ``content`` is blank.
        OSError: If either file cannot be written.

    Example:
        >>> write_backlog("# Backlog\\n", "/tmp/b.md", "/tmp/b.json")  # doctest: +SKIP
    """
    if not content.strip():
        raise ValueError("Backlog content is empty")
    write_doc(content, md_path)
    data = _validator().convert_backlog_md_to_json(content)
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


from lib.validators import (  # noqa: F401  (re-exports for back-compat)
    validate_architecture_content,
    validate_backlog_content,
)
