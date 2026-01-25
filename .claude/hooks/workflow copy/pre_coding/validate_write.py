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


# Add parent directory to import from utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.json import read_stdin_json  # type: ignore
from utils.cache import set_cache, get_cache  # type: ignore
from utils.output import block_response, block_stoppage, allow_stoppage, print_and_exit  # type: ignore
from utils.project import build_project_path  # type: ignore
from roadmap.utils import (
    get_current_milestone_full_name,
    get_current_version,
    get_current_phase_full_name,
)

session_id = get_cache("session_id", MAIN_CACHE_PATH)

# Code file extensions
CODE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".html", ".py")

BASE_REPORT_FILE_PATH = (
    f"project/{get_current_milestone_full_name()}_{get_current_phase_full_name()}"
)
REPORTS_FILE_PATH = {
    "explore": f"{BASE_REPORT_FILE_PATH}/codebase-status/codebase-status_{session_id}_{datetime.now().strftime('%m%d%y')}.md",
    "plan": f"{BASE_REPORT_FILE_PATH}/plans/plan_{session_id}_{datetime.now().strftime('%m%d%y')}.md",
    "consult": f"{BASE_REPORT_FILE_PATH}/plans/plan_{session_id}_{datetime.now().strftime('%m%d%y')}.md",
}


def main() -> None:
    # Validate if subagent is triggered
    hook_input = read_stdin_json()
    current_phase = get_cache("current_phase", MAIN_CACHE_PATH)
    file_path = hook_input.get("tool_input", {}).get("file_path", "")
    is_implement_active = get_cache("is_implement_active", MAIN_CACHE_PATH)

    abs_explore_report_file_path = Path(REPORTS_FILE_PATH["explore"]).absolute()
    abs_plan_report_file_path = Path(REPORTS_FILE_PATH["plan"]).absolute()
    abs_consult_report_file_path = Path(REPORTS_FILE_PATH["consult"]).absolute()

    if not is_implement_active:
        print_and_exit("/implement is not active. Proceeding with non-workflow state")

    if current_phase == "explore" and file_path != abs_explore_report_file_path:
        set_cache("invalid_explore_file_path", True, EXPLORE_CACHE_PATH)
        block_response("Cannot write to this file path")
    elif current_phase == "plan" and file_path != abs_plan_report_file_path:
        set_cache("invalid_plan_file_path", True, PLAN_CACHE_PATH)
        block_response("Cannot write to this file path")
    elif current_phase == "consult" and file_path != abs_consult_report_file_path:
        set_cache("invalid_consult_file_path", True, CONSULT_CACHE_PATH)
        block_response("Cannot write to this file path")


if __name__ == "__main__":
    main()
