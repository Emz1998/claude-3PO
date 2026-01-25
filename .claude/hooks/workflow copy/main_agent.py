#!/usr/bin/env python3
"""Delete workflow cache file."""


from datetime import datetime
import sys
from pathlib import Path
import json
from typing import Any

# Add parent directory to import from utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.json import read_stdin_json  # type: ignore
from utils.cache import set_cache, get_cache  # type: ignore
from utils.output import block_response, block_stoppage, allow_stoppage, print_and_exit  # type: ignore
from utils.project import build_project_path  # type: ignore

from roadmap.utils import (
    get_current_milestone_parallel_agents,
    load_roadmap,
    get_roadmap_path,
    get_current_version,
    get_current_milestone,
    are_tasks_completed_in_current_milestone,
)


ROADMAP = load_roadmap() or {}
CURRENT_MILESTONE = get_current_milestone() or {}

# Code file extensions
CODE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".html", ".py")


# CACHE PATHS

EXPLORE_CACHE_PATH = Path(".claude/hooks/cache/explore.json")
PLAN_CACHE_PATH = Path(".claude/hooks/cache/plan.json")
CONSULT_CACHE_PATH = Path(".claude/hooks/cache/consult.json")
CODE_CACHE_PATH = Path(".claude/hooks/cache/code.json")
MAIN_CACHE_PATH = Path(".claude/hooks/cache/main.json")


session_id = get_cache("session_id", MAIN_CACHE_PATH)


test_input: dict[str, Any] = {
    "session_id": "55e03575-bd44-43b2-bcb2-2214bad7a612",
    "transcript_path": "/home/emhar/.claude/projects/-home-emhar-avaris-ai/55e03575-bd44-43b2-bcb2-2214bad7a612.jsonl",
    "cwd": "/home/emhar/avaris-ai",
    "permission_mode": "bypassPermissions",
    "hook_event_name": "PreToolUse",
    "tool_name": "Task",
    "tool_input": {
        "description": "Analyze utils directory structure",
        "prompt": "Explore the utils/ directory thoroughly. I need to understand:\n1. All files in the utils directory and subdirectories\n2. What each utility file does\n3. Which utilities are redundant or duplicated\n4. Which utilities are actually used in the codebase\n5. File sizes and line counts\n6. Dependencies between utility files\n\nProvide a comprehensive analysis to help with refactoring to reduce complexity and remove redundant code.",
        "subagent_type": "frontend-engineer",
        "run_in_background": True,
    },
    "tool_use_id": "toolu_01RbYELyUGtDAsqrk9CTgyEC",
} or {}

test_cache: dict[str, Any] = {
    "current_workflow_phase": "coding",
    "current_code_workflow_phase": "validate",
    "is_implement_active": True,
    "triggered_subagents": ["frontend-engineer"],
} or {}

test_post_tool_use: dict[str, Any] = {
    "session_id": "58859241-fc2f-41f0-b829-9baac891dd31",
    "transcript_path": "/home/emhar/.claude/projects/-home-emhar-avaris-ai/58859241-fc2f-41f0-b829-9baac891dd31.jsonl",
    "cwd": "/home/emhar/avaris-ai",
    "permission_mode": "default",
    "hook_event_name": "PostToolUse",
    "tool_name": "Skill",
    "tool_input": {
        "skill": "hooks-management",
        "args": "revise @.claude/hooks/guardrails/codebase_explorer.py. I want you to add a dependency check that will block if dependency hasnt met. The dependencies are:\n\n1. implement is triggered and active\n2. The todo file is read",
    },
    "tool_response": {"success": True, "commandName": "hooks-management"},
    "tool_use_id": "toolu_01FsV4JJLyQtZykTCAjYYQav",
} or {}


def log_pre_coding_completion(skill_name: str, hook_event_name: str) -> None:
    if hook_event_name != "PostToolUse":
        return

    if skill_name == "explore":
        set_cache("explore_phase", "completed", MAIN_CACHE_PATH)
    elif skill_name == "plan":
        set_cache("plan_phase", "completed", MAIN_CACHE_PATH)
    elif skill_name == "consult":
        set_cache("consult_phase", "completed", MAIN_CACHE_PATH)
    elif skill_name == "code":
        set_cache("code_phase", "completed", MAIN_CACHE_PATH)


def workflow_transition_guardrail(skill_name: str) -> None:
    # Validate if subagent is triggered
    is_implement_active = get_cache("is_implement_active", MAIN_CACHE_PATH)
    current_workflow_phase = skill_name

    is_todo_read = get_cache("is_todo_read", MAIN_CACHE_PATH)

    explore_phase_status = get_cache("explore_phase", MAIN_CACHE_PATH)
    plan_phase_status = get_cache("plan_phase", MAIN_CACHE_PATH)
    consult_phase_status = get_cache("consult_phase", MAIN_CACHE_PATH)

    if not is_implement_active:
        print_and_exit("/implement is not active. Proceeding with non-workflow state")

    set_cache("current_workflow_phase", skill_name, MAIN_CACHE_PATH)

    if current_workflow_phase == "explore" and not is_todo_read:
        set_cache("invalid_skill", True, EXPLORE_CACHE_PATH)
        block_response("Cannot use plan skill before explore phase is done")
    elif current_workflow_phase == "plan" and explore_phase_status != "completed":
        set_cache("invalid_skill", True, PLAN_CACHE_PATH)
        block_response("Cannot use consult skill before explore phase is done")
    elif current_workflow_phase == "consult" and plan_phase_status != "completed":
        set_cache("invalid_skill", True, EXPLORE_CACHE_PATH)
        block_response("Cannot use code skill before plan phase is done")
    elif current_workflow_phase == "code" and consult_phase_status != "completed":
        set_cache("invalid_skill", True, CODE_CACHE_PATH)
        block_response("Cannot use code skill before consult phase is done")


def tdd_guardrail(skill_name: str) -> None:
    testing_strategy = get_cache("testing_strategy", MAIN_CACHE_PATH)
    if testing_strategy != "TDD":
        return

    is_failing_tests_created = get_cache("is_failing_tests_created", MAIN_CACHE_PATH)

    if skill_name == "tdd:failing-tests":



def coding_guardrail(skill_name: str, args: list[str]) -> None:

    current_workflow_phase = test_cache.get("current_workflow_phase", "")
    current_code_workflow_phase = test_cache.get("current_code_workflow_phase", "")
    is_task_in_progress = test_cache.get("is_task_in_progress", False)
    is_task_completed = test_cache.get("is_task_completed", False)

    is_implement_active = test_cache.get("is_implement_active", False)

    if not is_implement_active:
        print_and_exit("/implement is not active. Proceeding with non-workflow state")

    if (
        not current_workflow_phase == "coding"
        and not current_code_workflow_phase == "implement:task"
    ):
        return

    if skill_name != "log:task" or args != "in_progress" or not is_task_in_progress:
        block_response(
            f"Task is not in progress. Please log the task in_progress first."
        )

    if skill_name != "code_review" and not is_task_completed:
        block_response(f"Task is not completed. Please complete the task first.")


if __name__ == "__main__":

    main()
