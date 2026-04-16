#!/usr/bin/env python3
"""Unified PreToolUse dispatcher — routes to guardrail.py and recorder.py, injects reminders."""


import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts import validate_architecture, validate_product_vision, validate_constitution  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from hooks.workflow.hook import Hook  # type: ignore

CWD = Path.cwd().resolve()
ARCHITECTURE_MD_PATH = CWD / ".claude/projects/docs/architecture.md"
PRODUCT_VISION_MD_PATH = CWD / ".claude/projects/docs/product-vision.md"
CONSTITUTION_MD_PATH = CWD / ".claude/projects/docs/constitution.md"


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

    file_path: str = raw_input.get("tool_input", {}).get("file_path", "")

    architecture_md_path = str(ARCHITECTURE_MD_PATH)
    product_vision_md_path = str(PRODUCT_VISION_MD_PATH)
    constitution_md_path = str(CONSTITUTION_MD_PATH)

    content = raw_input.get("tool_input", {}).get("content", "")

    if file_path == architecture_md_path:
        md_errors = "Architecture", validate_architecture.validate(content)

    elif file_path == product_vision_md_path:
        md_errors = "Product Vision", validate_product_vision.validate(content)
    elif file_path == constitution_md_path:
        md_errors = "Constitution", validate_constitution.validate(content)

    else:
        Hook.advanced_block(
            hook_event_name,
            f"Blocked: Invalid specs file: {file_path}",
        )
        return

    file_name, errors = md_errors

    if errors:
        Hook.advanced_block(
            hook_event_name,
            f"Blocked: {file_name} Markdown validation errors:\n{'\n'.join(errors)}",
        )
        return

    Hook.system_message("Specs validation passed")


if __name__ == "__main__":
    main()
