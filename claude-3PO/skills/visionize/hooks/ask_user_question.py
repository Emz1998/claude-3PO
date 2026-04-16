#!/usr/bin/env python3
"""PreToolUse hook for AskUserQuestion — ensures only approved discovery questions are asked."""

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent / ".claude"))

from hooks.workflow.hook import Hook  # type: ignore

QUESTIONS_MD = Path(__file__).resolve().parent.parent / "questions.md"


def read_stdin() -> dict[str, Any]:
    raw_input = sys.stdin.read()
    return json.loads(raw_input)


def load_approved_questions(path: Path) -> list[str]:
    """Parse numbered questions from the questions.md file."""
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    return re.findall(r"^\d+\.\s+(.+)$", content, re.MULTILINE)


def validate_questions(asked: list[str], approved: list[str]) -> list[str]:
    """Return list of questions that are not in the approved set."""
    return [q for q in asked if q not in approved]


def main() -> None:
    raw_input = read_stdin()
    hook_event_name = raw_input.get("hook_event_name", "")
    tool_name = raw_input.get("tool_name", "")

    if tool_name != "AskUserQuestion":
        Hook.system_message("PreToolUse: Skipping non-AskUserQuestion tool use")

    questions_input = raw_input.get("tool_input", {}).get("questions", [])
    asked = [q.get("question", "") for q in questions_input]

    if not asked:
        Hook.system_message("AskUserQuestion: no questions to validate")

    if not QUESTIONS_MD.exists():
        Hook.advanced_block(hook_event_name, "Blocked: questions.md not found")

    approved = load_approved_questions(QUESTIONS_MD)

    if not approved:
        Hook.advanced_block(hook_event_name, "Blocked: no approved questions found in questions.md")

    rejected = validate_questions(asked, approved)

    if rejected:
        rejected_list = "\n".join(f"  - {q}" for q in rejected)
        Hook.advanced_block(
            hook_event_name,
            f"Blocked: questions not in approved list:\n{rejected_list}",
        )

    Hook.system_message("AskUserQuestion validation passed")


if __name__ == "__main__":
    main()
