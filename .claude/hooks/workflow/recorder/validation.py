import json
from typing import Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.hook import Hook
from workflow.constants.config import CODE_EXTENSIONS, TEST_EXTENSIONS, PLAN_DIR


def validate_coding_phase(file_path: str) -> tuple[bool, str]:
    if file_path.endswith(CODE_EXTENSIONS):
        return True, ""
    return False, "File is not a code file: " + file_path


def validate_test_file(file_path: str) -> tuple[bool, str]:
    if any(Path(file_path).match(test_extension) for test_extension in TEST_EXTENSIONS):
        return True, ""
    return False, "File is not a test file: " + file_path


def validate_plan_file(file_path: str) -> tuple[bool, str]:
    if Path(file_path).parent == PLAN_DIR:
        return True, ""
    return False, "File is not a plan file: " + file_path


def is_task_creation_phase(prompt: str) -> tuple[bool, str]:
    if prompt.startswith("/implement"):
        return True, ""
    return False, "Prompt is not a task creation prompt: " + prompt


def is_exploration_phase(last_agent: str) -> tuple[bool, str]:
    if last_agent == "task-manager":
        return True, ""
    return False, "Agent is not a task manager: " + last_agent


def is_planning_phase(last_agent: str) -> tuple[bool, str]:
    if last_agent == "Explore":
        return True, ""
    return False, "Last agent is not a plan consultant: " + last_agent


def is_tests_creation_phase(last_tool: str, TDD: bool) -> tuple[bool, str]:
    if last_tool == "ExitPlanMode" and TDD:
        return True, ""
    return False, "Last tool is not a test creation tool: " + last_tool


def is_code_phase(last_agent: str) -> tuple[bool, str]:
    if last_agent == "test-engineer":
        return True, ""
    return False, "Last agent is not a test engineer: " + last_agent
