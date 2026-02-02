#!/usr/bin/env python3
"""Phase transition guard hook for workflow enforcement."""

import json
import sys
from pathlib import Path
from typing import Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json  # type: ignore
from roadmap.utils import get_test_strategy  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from state import get_state, set_state, initialize_deliverables_state  # type: ignore
from _utils import validate_order  # type: ignore

DEFAULT_STATE_FILE_PATH = Path(__file__).parent / "state.json"

PHASE_ORDER = ["explore", "plan", "plan-consult", "code", "commit"]
TDD_PHASE_ORDER = [
    "write_test",
    "review_test",
    "implement",
    "code-review",
    "refactor",
    "validate",
]
TEST_AFTER_PHASE_ORDER = [
    "implement",
    "code-review",
    "write_test",
    "review_test",
    "refactor",
    "validate",
]


def complete_phase_order(test_strategy: str) -> list[str]:
    code_idx = PHASE_ORDER.index("code")

    before = PHASE_ORDER[:code_idx]
    after = PHASE_ORDER[code_idx + 1 :]  # skips "code"

    if test_strategy == "tdd":
        return before + TDD_PHASE_ORDER + after

    if test_strategy == "test_after":
        return before + TEST_AFTER_PHASE_ORDER + after

    return before + after


def main() -> None:
    is_workflow_active = get_state("workflow_active")
    if not is_workflow_active:
        sys.exit(0)
    hook_input = read_stdin_json()
    hook_event_name = hook_input.get("hook_event_name", "")
    tool_name = hook_input.get("tool_name", "")

    current_phase = get_state("current_phase")
    phase_order = complete_phase_order("tdd")
    if not hook_input:
        sys.exit(0)
    if hook_event_name != "PreToolUse":
        return
    if tool_name != "Skill":
        return
    skill = hook_input.get("tool_input", {}).get("skill", "")
    is_valid, error_message = validate_order(current_phase, skill, phase_order)
    print(
        f"Current phase: {current_phase}, Skill: {skill}, Is valid: {is_valid}, Error message: {error_message}"
    )
    if not is_valid:
        print(error_message, file=sys.stderr)
        sys.exit(2)
