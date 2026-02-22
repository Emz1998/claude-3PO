"""File I/O utilities with error handling."""

import json
from pathlib import Path
from typing import Any


class FileReadError(Exception):
    """Raised when a file cannot be read."""

    pass


def read_file(file_path: str) -> str:
    """Read file content with error handling."""
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileReadError(f"File not found: {file_path}")
    except PermissionError:
        raise FileReadError(f"Permission denied: {file_path}")
    except UnicodeDecodeError:
        raise FileReadError(f"Invalid encoding: {file_path}")


def write_file(file_path: str, content: str) -> None:
    """Write content to file, overwriting existing content."""
    Path(file_path).write_text(content, encoding="utf-8")
