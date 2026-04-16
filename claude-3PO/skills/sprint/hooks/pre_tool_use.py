#!/usr/bin/env python3
"""PreToolUse hook for sprint.md — validates markdown and syncs sprint.json."""


import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import sprint_json_converter, validate_sprint_json, validate_sprint_md  # type: ignore

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent / ".claude"))

from hooks.workflow.hook import Hook  # type: ignore


def _resolve_paths(cwd: str) -> tuple[Path, Path]:
    """Resolve sprint file paths from the project cwd."""
    root = Path(cwd).resolve()
    return (
        root / ".claude/projects/sprint.md",
        root / ".claude/projects/sprint.json",
    )


def read_stdin() -> dict[str, Any]:
    raw_input = sys.stdin.read()
    return json.loads(raw_input)


def _get_content_for_write(tool_input: dict[str, Any]) -> str:
    """Extract content from a Write tool payload."""
    return tool_input.get("content", "")


def _get_content_for_edit(tool_input: dict[str, Any], sprint_md_path: Path, hook_event_name: str) -> str | None:
    """Simulate an Edit against the current sprint.md. Returns None if blocked."""
    old_string = tool_input.get("old_string", "")
    new_string = tool_input.get("new_string", "")

    if not sprint_md_path.exists():
        Hook.system_message("PreToolUse: sprint.md does not exist yet, skipping Edit validation")

    current = sprint_md_path.read_text(encoding="utf-8")

    if old_string not in current:
        Hook.advanced_block(hook_event_name, "Edit old_string not found in sprint.md")

    return current.replace(old_string, new_string, 1)


def _validate_content(content: str, hook_event_name: str) -> dict[str, Any] | None:
    """Run md and json validation. Returns parsed data on success, or blocks and exits."""
    md_errors = validate_sprint_md.validate(content)
    if md_errors:
        Hook.advanced_block(
            hook_event_name,
            f"Sprint Markdown validation errors:\n{'\n'.join(md_errors)}",
        )

    data = sprint_json_converter.convert(content)

    json_errors = validate_sprint_json.validate(data)
    if json_errors:
        Hook.advanced_block(
            hook_event_name,
            f"Sprint JSON schema validation errors:\n{'\n'.join(json_errors)}",
        )

    return data


def _sync_sprint_json(data: dict[str, Any], sprint_json_path: Path) -> None:
    """Write validated data to sprint.json."""
    sprint_json_path.parent.mkdir(parents=True, exist_ok=True)
    sprint_json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    raw_input = read_stdin()
    hook_event_name = raw_input.get("hook_event_name", "")
    tool_name = raw_input.get("tool_name", "")

    if tool_name not in ("Write", "Edit"):
        Hook.system_message("PreToolUse: Skipping non-write/edit tool use")

    cwd = raw_input.get("cwd", str(Path.cwd()))
    sprint_md_path, sprint_json_path = _resolve_paths(cwd)
    file_path = raw_input.get("tool_input", {}).get("file_path", "")

    if file_path != str(sprint_md_path):
        Hook.system_message(
            f"PreToolUse: Skipping non-sprint.md file: {file_path}. Expected: {sprint_md_path}"
        )

    tool_input = raw_input.get("tool_input", {})

    if tool_name == "Write":
        content = _get_content_for_write(tool_input)
    else:
        content = _get_content_for_edit(tool_input, sprint_md_path, hook_event_name)

    data = _validate_content(content, hook_event_name)
    _sync_sprint_json(data, sprint_json_path)

    Hook.system_message("Sprint validation passed")


if __name__ == "__main__":
    main()
