#!/usr/bin/env python3
"""Delete workflow cache file."""

from datetime import datetime
import sys
from pathlib import Path
import json

EXPLORE_CACHE_PATH = Path(".claude/hooks/cache/explore.json")
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


def validate_invocation(subagent_name: str) -> None:
    # Validate if subagent is triggered
    is_implement_active = get_cache("is_implement_active", MAIN_CACHE_PATH)

    if not is_implement_active:
        print_and_exit("/implement is not active. Proceeding with non-workflow state")

    if subagent_name != "codebase-explorer":
        set_cache("invalid_subagent", True, EXPLORE_CACHE_PATH)


def validate_completion(hook_tool_name: str, subagent_name: str):
    if hook_tool_name != "Task" and subagent_name != "codebase-explorer":
        print(f"Invalid Hook Inputs: {hook_tool_name}, {subagent_name} ")
        sys.exit(0)
    print("validate_completion")
    set_cache("explore_phase_done", True, MAIN_CACHE_PATH)


def get_codebase_status_file_path() -> str:
    file_name = f"codebase-status_{datetime.now().strftime('%Y%m%d')}_{session_id}.md"
    valid_file_path = build_project_path("codebase-status", file_name)
    return str(valid_file_path)


def validate_report(file_path: str) -> None:
    valid_file_path = get_codebase_status_file_path()
    if file_path != str(valid_file_path):
        set_cache("invalid_codebase_file_path", True, EXPLORE_CACHE_PATH)
    set_cache("is_codebase_report_done", True, EXPLORE_CACHE_PATH)


def add_context(old_prompt: str, additional_context: str) -> None:
    # new_prompt = f"{old_prompt}\n\n{additional_context}"
    set_cache("additional_context", additional_context, EXPLORE_CACHE_PATH)


def is_code_file(file_path: str) -> bool:
    """Check if file is a code file based on extension."""
    return file_path.endswith(CODE_EXTENSIONS)


def block_coding(file_path: str) -> None:
    """Block coding operations on code files."""
    if is_code_file(file_path):
        set_cache("block_coding", True, EXPLORE_CACHE_PATH)


def guardrail() -> None:
    hook_input = read_stdin_json()
    hook_event_name = hook_input.get("hook_event_name", "")
    hook_tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if hook_event_name == "PreToolUse":
        if hook_tool_name == "Task":
            prompt = tool_input.get("prompt", "")
            subagent_name = tool_input.get("subagent_type", "")
            validate_invocation(subagent_name)
            add_context(
                prompt,
                f"Only Write the todays date to this file path: {get_codebase_status_file_path()}. Do not do anything else.",
            )
        elif hook_tool_name == "Write":
            file_path = tool_input.get("file_path", "")
            validate_report(file_path)
            block_coding(file_path)

    elif hook_event_name == "PostToolUse":
        subagent_name = tool_input.get("subagent_type", "")
        validate_completion(hook_tool_name, subagent_name)
    elif hook_event_name == "Stop":
        is_codebase_report_done = get_cache(
            "is_codebase_report_done", EXPLORE_CACHE_PATH
        )
        if is_codebase_report_done:
            allow_stoppage("Codebase exploration completed successfully")
        else:
            file_path = hook_input.get("file_path", "")
            block_stoppage("Codebase report not yet written")
    else:
        sys.exit(0)


def main() -> None:
    guardrail()
    is_invalid_subagent = get_cache("invalid_subagent", EXPLORE_CACHE_PATH)
    is_invalid_codebase_file_path = get_cache(
        "invalid_codebase_file_path", EXPLORE_CACHE_PATH
    )
    is_block_coding = get_cache("block_coding", EXPLORE_CACHE_PATH)
    additional_context = get_cache("additional_context", EXPLORE_CACHE_PATH)
    if is_invalid_subagent or is_invalid_codebase_file_path or is_block_coding:
        block_response("Invalid subagent, codebase file path, or block coding")
    if additional_context:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Allowing the tool use to write the codebase status",
                "updatedInput": {
                    "description": "Test dry-run",
                    "subagent_type": "codebase-explorer",
                    "prompt": additional_context,
                },
            },
        }
        print(json.dumps(output))


if __name__ == "__main__":
    main()
