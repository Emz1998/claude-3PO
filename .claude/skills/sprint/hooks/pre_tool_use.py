#!/usr/bin/env python3
"""Unified PreToolUse dispatcher — routes to guardrail.py and recorder.py, injects reminders."""

from fileinput import filelineno
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts import sprint_json_converter, validate_sprint_json, validate_sprint_md  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from hooks.workflow.hook import Hook  # type: ignore

SPRINT_MD_PATH = Path.cwd().resolve() / ".claude/projects/sprint.md"
SPRINT_JSON_PATH = Path.cwd().resolve() / ".claude/projects/sprint.json"


def read_stdin() -> dict[str, Any]:
    raw_input = sys.stdin.read()
    return json.loads(raw_input)


def main() -> None:
    raw_input = read_stdin()
    hook_event_name = raw_input.get("hook_event_name", "")
    tool_name = raw_input.get("tool_name", "")

    if tool_name not in ("Write", "Edit"):
        Hook.system_message("PreToolUse: Skipping non-write/edit tool use")
        return

    file_path = raw_input.get("tool_input", {}).get("file_path", "")

    if file_path != str(SPRINT_MD_PATH):
        Hook.system_message(
            f"PreToolUse: Skipping non-sprint.md file: {file_path}. Expected: {SPRINT_MD_PATH}"
        )
        return

    content = raw_input.get("tool_input", {}).get("content", "")

    md_errors = validate_sprint_md.validate(content)

    if md_errors:
        Hook.advanced_block(
            hook_event_name,
            f"Sprint Markdown validation errors:\n{'\n'.join(md_errors)}",
        )
        return

    data = sprint_json_converter.convert(content)

    json_schema_error = validate_sprint_json.validate(data)
    if json_schema_error:
        Hook.advanced_block(
            hook_event_name,
            f"Sprint JSON schema validation errors:\n{'\n'.join(json_schema_error)}",
        )
        return

    SPRINT_JSON_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    Hook.system_message("Sprint validation passed")


if __name__ == "__main__":
    main()
