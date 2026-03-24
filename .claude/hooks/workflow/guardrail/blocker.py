import json
from typing import Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook
from workflow.constants.config import CODE_EXTENSIONS, TEST_EXTENSIONS, PLAN_DIR
from workflow.session_state import SessionState


def block_exploration(agent: str, message: str) -> None:
    if agent == "Explore":
        Hook.advanced_block("PreToolUse", message or "Exploration is blocked for now")
        return
    Hook.system_message("Exploration Allowed")


def block_planning(agent: str, message: str) -> None:
    if agent == "Plan":
        Hook.advanced_block("PreToolUse", message or "Planning is blocked for now")
        return

    Hook.system_message("Planning Allowed")


def block_test_creation(file_path: str, message: str) -> None:
    if any(Path(file_path).match(test_extension) for test_extension in TEST_EXTENSIONS):
        Hook.advanced_block("PreToolUse", message or "Test creation is blocked for now")
        return

    Hook.system_message("Test Creation Allowed")


def block_coding(file_path: str, message: str, session: SessionState) -> None:
    if file_path.endswith(CODE_EXTENSIONS):
        Hook.advanced_block("PreToolUse", message or "Coding is blocked for now")
        return

    Hook.system_message("Coding Allowed")


def block_pr_creation(command: str, message: str) -> None:
    if "gh pr create" in command or "pr_manager.py create" in command:
        Hook.advanced_block("PreToolUse", message or "PR creation is blocked for now")
        return

    Hook.system_message("PR Creation Allowed")
