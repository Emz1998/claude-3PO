#!/usr/bin/env python3
"""Delete workflow cache file."""

from asyncio import Transport
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
    get_owners_with_completed_deps,
    load_roadmap,
    get_roadmap_path,
    get_current_version,
    get_current_milestone,
)


MAIN_CACHE_PATH = Path(".claude/hooks/cache/main.json")
ROADMAP = load_roadmap() or {}
CURRENT_MILESTONE = get_current_milestone() or {}

# Code file extensions
CODE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".html", ".py")
CODE_CACHE_PATH = Path(".claude/hooks/cache/code.json")
TRANSCRIPT_CACHE_PATH = Path(".claude/hooks/cache/transcript.json")

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
        "subagent_type": "Explore",
        "run_in_background": True,
    },
    "tool_use_id": "toolu_01RbYELyUGtDAsqrk9CTgyEC",
} or {}


def main() -> None:
    hook_input = test_input
    subagent_name = hook_input.get("tool_input", {}).get("subagent_type", "")
    run_in_background = hook_input.get("tool_input", {}).get("run_in_background", False)
    current_workflow_phase = get_cache("current_workflow_phase", MAIN_CACHE_PATH)
    current_code_workflow_phase = get_cache(
        "current_code_workflow_phase", CODE_CACHE_PATH
    )

    is_implement_active = get_cache("is_implement_active", MAIN_CACHE_PATH)

    if not is_implement_active:
        print_and_exit("/implement is not active. Proceeding with non-workflow state")

    if (
        not current_workflow_phase == "coding"
        and not current_code_workflow_phase == "implement:task"
    ):
        return

    task_owners = get_owners_with_completed_deps(ROADMAP, CURRENT_MILESTONE)
    triggered_subagents = get_cache("triggered_subagents", CODE_CACHE_PATH)

    if subagent_name not in task_owners and not run_in_background:
        block_response(
            f"Subagent {subagent_name} is not a task owner. Proceeding with non-workflow state"
        )
    if subagent_name in triggered_subagents:
        block_response(
            f"Subagent {subagent_name} has already been triggered. Proceeding with non-workflow state"
        )

    triggered_subagents.append(subagent_name)
    set_cache("triggered_subagents", triggered_subagents, CODE_CACHE_PATH)

    if set(task_owners) - set(triggered_subagents):
        print_and_exit(
            f"Missing task owners: {set(task_owners) - set(triggered_subagents)}. Please trigger the missing subagents in parallel with {", ".join(triggered_subagents)}"
        )


if __name__ == "__main__":

    main()
