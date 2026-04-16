"""specs_writer.py — Writes specs docs (md + json for backlog) to disk.

Validates content before writing. Used by AgentReportGuard for
auto-writing architect and backlog outputs.
"""

import json
import sys
from pathlib import Path

# Add skills directories to path for validator imports
_PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PLUGIN_ROOT / "skills" / "architect" / "scripts"))
sys.path.insert(0, str(_PLUGIN_ROOT / "skills" / "backlog" / "scripts"))

from validate_architecture import validate as _validate_arch
from validate_backlog_md import validate as _validate_backlog_md
from backlog_json_converter import convert as _convert_backlog


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
    data = _convert_backlog(content)
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


def validate_architecture_content(content: str) -> list[str]:
    """Validate architecture content against template. Returns error list."""
    return _validate_arch(content)


def validate_backlog_content(content: str) -> list[str]:
    """Validate backlog markdown content. Returns error list."""
    return _validate_backlog_md(content)
