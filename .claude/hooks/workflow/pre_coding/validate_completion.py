#!/usr/bin/env python3
"""Delete workflow cache file."""

from datetime import datetime
import sys
from pathlib import Path
import json


# Add parent directory to import from utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.json import read_stdin_json  # type: ignore
from utils.cache import set_cache, get_cache  # type: ignore
from utils.output import block_response, block_stoppage, allow_stoppage, print_and_exit  # type: ignore
from utils.project import build_project_path  # type: ignore


MAIN_CACHE_PATH = Path(".claude/hooks/cache/main.json")

# Code file extensions
CODE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".html", ".py")


session_id = get_cache("session_id", MAIN_CACHE_PATH)


def main() -> None:
    hook_input = read_stdin_json()
    subagent_name = hook_input.get("tool_input", {}).get("subagent_type", "")
    current_phase = get_cache("current_phase", MAIN_CACHE_PATH)

    is_implement_active = get_cache("is_implement_active", MAIN_CACHE_PATH)

    if not is_implement_active:
        print_and_exit("/implement is not active. Proceeding with non-workflow state")

    if current_phase == "explore" and subagent_name == "codebase-explorer":
        set_cache("explore_phase_done", True, MAIN_CACHE_PATH)
    elif current_phase == "plan" and subagent_name == "planner":
        set_cache("plan_phase_done", True, MAIN_CACHE_PATH)
    elif current_phase == "consult" and subagent_name == "consultant":
        set_cache("consultant_phase_done", True, MAIN_CACHE_PATH)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
