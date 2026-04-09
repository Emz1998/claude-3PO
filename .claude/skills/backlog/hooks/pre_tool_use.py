#!/usr/bin/env python3
"""Unified PreToolUse dispatcher — routes to guardrail.py and recorder.py, injects reminders."""


import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts import backlog_json_converter, validate_backlog_json, validate_backlog_md  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from hooks.workflow.hook import Hook  # type: ignore

BACKLOG_MD_PATH = Path.cwd().resolve() / ".claude/projects/backlog/backlog.md"
BACKLOG_JSON_PATH = Path.cwd().resolve() / ".claude/projects/backlog/backlog.json"


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

    if file_path != str(BACKLOG_MD_PATH):
        Hook.system_message(
            f"PreToolUse: Skipping non-backlog.md file: {file_path}. Expected: {BACKLOG_MD_PATH}"
        )
        return

    content = ""

    if tool_name == "Write":
        content = raw_input.get("tool_input", {}).get("content", "")
    elif tool_name == "Edit":
        tool_input = raw_input.get("tool_input", {})
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")
        if not BACKLOG_MD_PATH.exists():
            Hook.system_message("PreToolUse: backlog.md does not exist yet, skipping Edit validation")
            return
        current = BACKLOG_MD_PATH.read_text(encoding="utf-8")
        if old_string not in current:
            Hook.advanced_block(hook_event_name, "Edit old_string not found in backlog.md")
            return
        content = current.replace(old_string, new_string, 1)

    md_errors = validate_backlog_md.validate(content)

    if md_errors:
        Hook.advanced_block(
            hook_event_name,
            f"Backlog Markdown validation errors:\n{'\n'.join(md_errors)}",
        )
        return

    data = backlog_json_converter.convert(content)

    json_schema_error = validate_backlog_json.validate(data)
    if json_schema_error:
        Hook.advanced_block(
            hook_event_name,
            f"Backlog JSON schema validation errors:\n{'\n'.join(json_schema_error)}",
        )
        return

    if not BACKLOG_JSON_PATH.parent.exists():
        BACKLOG_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    BACKLOG_JSON_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    Hook.system_message("Backlog validation passed")


if __name__ == "__main__":
    main()
