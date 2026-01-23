#!/usr/bin/env python3
"""Delete workflow cache file."""

from datetime import datetime
import sys
from pathlib import Path
import json

EXPLORE_CACHE_PATH = Path(".claude/hooks/cache/explore.json")
PLAN_CACHE_PATH = Path(".claude/hooks/cache/plan.json")
CONSULT_CACHE_PATH = Path(".claude/hooks/cache/consult.json")
MAIN_CACHE_PATH = Path(".claude/hooks/cache/main.json")

# Code file extensions
CODE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".html", ".py")


# Add parent directory to import from utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.json import read_stdin_json  # type: ignore
from utils.cache import set_cache, get_cache  # type: ignore
from utils.output import block_response, block_stoppage, allow_stoppage, print_and_exit  # type: ignore
from utils.project import build_project_path  # type: ignore

session_id = get_cache("session_id", MAIN_CACHE_PATH)


def main() -> None:
    # Validate if subagent is triggered
    hook_input = read_stdin_json()
    skill_name = hook_input.get("tool_input", {}).get("skill", "")
    is_implement_active = get_cache("is_implement_active", MAIN_CACHE_PATH)

    is_explore_phase_done = get_cache("explore_phase_done", EXPLORE_CACHE_PATH)
    is_plan_phase_done = get_cache("plan_phase_done", PLAN_CACHE_PATH)
    is_consult_phase_done = get_cache("consult_phase_done", CONSULT_CACHE_PATH)

    if not is_implement_active:
        print_and_exit("/implement is not active. Proceeding with non-workflow state")

    set_cache("current_phase", skill_name, MAIN_CACHE_PATH)

    current_phase = get_cache("current_phase", MAIN_CACHE_PATH)

    if current_phase == "explore" and not is_explore_phase_done:
        set_cache("invalid_skill", True, EXPLORE_CACHE_PATH)
        block_response("Cannot use plan skill before explore phase is done")
    elif current_phase == "plan" and not is_plan_phase_done:
        set_cache("invalid_skill", True, PLAN_CACHE_PATH)
        block_response("Cannot use consult skill before plan phase is done")
    elif current_phase == "consult" and not is_consult_phase_done:
        set_cache("invalid_skill", True, EXPLORE_CACHE_PATH)
        block_response("Cannot use code skill before consult phase is done")


if __name__ == "__main__":
    main()
