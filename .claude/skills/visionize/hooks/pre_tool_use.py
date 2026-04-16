#!/usr/bin/env python3
"""PreToolUse hook for product-vision.md — validates markdown structure."""


import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import validate_product_vision  # type: ignore

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent / ".claude"))

from hooks.workflow.hook import Hook  # type: ignore


def _resolve_path(cwd: str) -> Path:
    """Resolve product-vision.md path from the project cwd."""
    return Path(cwd).resolve() / ".claude/projects/docs/product-vision.md"


def read_stdin() -> dict[str, Any]:
    raw_input = sys.stdin.read()
    return json.loads(raw_input)


def _get_content_for_write(tool_input: dict[str, Any]) -> str:
    """Extract content from a Write tool payload."""
    return tool_input.get("content", "")


def _get_content_for_edit(tool_input: dict[str, Any], file_on_disk: Path, hook_event_name: str) -> str:
    """Simulate an Edit against the current file. Exits if blocked."""
    old_string = tool_input.get("old_string", "")
    new_string = tool_input.get("new_string", "")

    if not file_on_disk.exists():
        Hook.system_message("PreToolUse: product-vision.md does not exist yet, skipping Edit validation")

    current = file_on_disk.read_text(encoding="utf-8")

    if old_string not in current:
        Hook.advanced_block(hook_event_name, "Edit old_string not found in product-vision.md")

    return current.replace(old_string, new_string, 1)


def main() -> None:
    raw_input = read_stdin()
    hook_event_name = raw_input.get("hook_event_name", "")
    tool_name = raw_input.get("tool_name", "")

    if tool_name not in ("Write", "Edit"):
        Hook.system_message("PreToolUse: Skipping non-write/edit tool use")

    cwd = raw_input.get("cwd", str(Path.cwd()))
    vision_path = _resolve_path(cwd)
    file_path = raw_input.get("tool_input", {}).get("file_path", "")

    if file_path != str(vision_path):
        Hook.system_message(
            f"PreToolUse: Skipping non-product-vision file: {file_path}. Expected: {vision_path}"
        )

    tool_input = raw_input.get("tool_input", {})

    if tool_name == "Write":
        content = _get_content_for_write(tool_input)
    else:
        content = _get_content_for_edit(tool_input, Path(file_path), hook_event_name)

    errors = validate_product_vision.validate(content)

    if errors:
        Hook.advanced_block(
            hook_event_name,
            f"Blocked: Product Vision validation errors:\n{'\n'.join(errors)}",
        )

    Hook.system_message("Product Vision validation passed")


if __name__ == "__main__":
    main()
