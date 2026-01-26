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
from utils.project import build_project_path, BASE_PATH  # type: ignore


# CACHE PATHS
SUBAGENTS_CACHE_PATH = Path(".claude/hooks/cache/subagents.json")
MAIN_CACHE_PATH = Path(".claude/hooks/cache/main.json")
CODEBASE_EXPLORER_CACHE_PATH = Path(".claude/hooks/cache/codebase-explorer.json")

session_id = get_cache("session_id", MAIN_CACHE_PATH)

PROJECT_BASE_PATH = BASE_PATH


# REPORT_FILE_PATH
REPORT_FILE_PATH = (
    PROJECT_BASE_PATH
    / "codebase-status"
    / f"codebase-status_{session_id}_{datetime.now().strftime('%m%d%Y')}.md"
)

# TODO_FILE_PATH

TODO_FILE_PATH = (
    PROJECT_BASE_PATH / f"todo_{session_id}_{datetime.now().strftime('%m%d%Y')}.md"
)


test_write_tool: dict[str, Any] = {
    "session_id": "55e03575-bd44-43b2-bcb2-2214bad7a612",
    "transcript_path": "/home/emhar/.claude/projects/-home-emhar-avaris-ai/55e03575-bd44-43b2-bcb2-2214bad7a612.jsonl",
    "cwd": "/home/emhar/avaris-ai",
    "permission_mode": "bypassPermissions",
    "hook_event_name": "PreToolUse",
    "tool_name": "Write",
    "tool_input": {
        "file_path": str(REPORT_FILE_PATH.absolute()),
        "content": '"""File I/O utilities with error handling."""\n\nimport json\nfrom pathlib import Path\nfrom typing import Any\n\n\nclass FileReadError(Exception):\n    """Raised when a file cannot be read."""\n    pass\n\n\ndef read_file(file_path: str) -> str:\n    """Read file content with error handling."""\n    try:\n        return Path(file_path).read_text(encoding="utf-8")\n    except FileNotFoundError:\n        raise FileReadError(f"File not found: {file_path}")\n    except PermissionError:\n        raise FileReadError(f"Permission denied: {file_path}")\n    except UnicodeDecodeError:\n        raise FileReadError(f"Invalid encoding: {file_path}")\n\n\ndef write_file(file_path: str, content: str) -> None:\n    """Write content to file, overwriting existing content."""\n    Path(file_path).write_text(content, encoding="utf-8")\n\n\ndef read_json(file_path: str, default: dict | None = None) -> dict[str, Any]:\n    """Read JSON file with fallback to default."""\n    try:\n        return json.loads(read_file(file_path))\n    except (FileReadError, json.JSONDecodeError):\n        return default if default is not None else {}\n\n\ndef write_json(data: dict[str, Any], file_path: str, indent: int = 2) -> None:\n    """Write data to JSON file."""\n    Path(file_path).write_text(json.dumps(data, indent=indent), encoding="utf-8")\n\n\ndef output_json(data: dict[str, Any]) -> None:\n    """Output JSON to stdout."""\n    print(json.dumps(data))\n\n\ndef extract_slash_command_name(raw_command: str = "") -> str:\n    """Extract command name from a slash-prefixed prompt."""\n    if not raw_command or not raw_command.startswith("/"):\n        return ""\n    return raw_command[1:].split(" ")[0]\n',
    },
    "tool_use_id": "toolu_0142eG1nv1oi1qGK6HT75sjf",
} or {}


test_stop_input: dict[str, Any] = {
    "session_id": "a499e088-d35b-4be0-a3cc-1e9452f5fa1c",
    "transcript_path": "/home/emhar/.claude/projects/-home-emhar-avaris-ai/a499e088-d35b-4be0-a3cc-1e9452f5fa1c.jsonl",
    "cwd": "/home/emhar/avaris-ai",
    "permission_mode": "bypassPermissions",
    "hook_event_name": "Stop",
    "stop_hook_active": False,
} or {}

test_bash_tool: dict[str, Any] = {
    "session_id": "55e03575-bd44-43b2-bcb2-2214bad7a612",
    "transcript_path": "/home/emhar/.claude/projects/-home-emhar-avaris-ai/55e03575-bd44-43b2-bcb2-2214bad7a612.jsonl",
    "cwd": "/home/emhar/avaris-ai",
    "permission_mode": "bypassPermissions",
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
    "tool_input": {
        "command": "python -c \"from .claude.hooks.utils import read_file, write_file, extract_slash_command_name, load_json\" 2>&1 || python -c \"import sys; sys.path.insert(0, '.claude/hooks'); from utils import read_file, write_file, extract_slash_command_name, load_json; print('All imports successful')\"",
        "description": "Verify utils imports work",
    },
    "tool_use_id": "toolu_01QeWtdvyfTKpmN8aMymh2re",
} or {}

test_read_tool = {
    "session_id": "55e03575-bd44-43b2-bcb2-2214bad7a612",
    "transcript_path": "/home/emhar/.claude/projects/-home-emhar-avaris-ai/55e03575-bd44-43b2-bcb2-2214bad7a612.jsonl",
    "cwd": "/home/emhar/avaris-ai",
    "permission_mode": "bypassPermissions",
    "hook_event_name": "PreToolUse",
    "tool_name": "Read",
    "tool_input": {"file_path": str(TODO_FILE_PATH.absolute())},
    "tool_use_id": "toolu_01PsGUnKmeQmcLef63SzMYBP",
} or {}

test_cache: dict[str, Any] = {
    "current_workflow_phase": "coding",
    "current_code_workflow_phase": "validate",
    "is_implement_active": True,
    "triggered_subagents": ["frontend-engineer"],
} or {}

test_post_tool_use_input: dict[str, Any] = {
    "session_id": "55e03575-bd44-43b2-bcb2-2214bad7a612",
    "transcript_path": "/home/emhar/.claude/projects/-home-emhar-avaris-ai/55e03575-bd44-43b2-bcb2-2214bad7a612.jsonl",
    "cwd": "/home/emhar/avaris-ai",
    "permission_mode": "bypassPermissions",
    "hook_event_name": "PostToolUse",
    "tool_name": "Write",
    "tool_input": {
        "command": "rm /home/emhar/avaris-ai/.claude/hooks/utils/log_manager.py",
        "description": "Remove unused log_manager.py",
    },
    "tool_response": {
        "stdout": "",
        "stderr": "",
        "interrupted": False,
        "isImage": False,
    },
    "tool_use_id": "toolu_01Qko4h5Q1SZHZMphdMwUhyd",
} or {}


def set_tool_active(hook_input: dict[str, Any]) -> None:
    tool_name = hook_input.get("tool_name", "")
    hook_event_name = hook_input.get("hook_event_name", "")
    tool_status = {
        "name": tool_name,
        "status": "inactive",
    }
    if hook_event_name == "PreToolUse":
        tool_status["status"] = "active"
        set_cache("recent_tool_status", tool_status, CODEBASE_EXPLORER_CACHE_PATH)


def set_tool_inactive(hook_input: dict[str, Any]) -> None:
    tool_name = hook_input.get("tool_name", "")
    hook_event_name = hook_input.get("hook_event_name", "")
    tool_status = {
        "name": tool_name,
        "status": "inactive",
    }
    if hook_event_name == "PostToolUse":
        tool_status["status"] = "inactive"
        set_cache("recent_tool_status", tool_status, CODEBASE_EXPLORER_CACHE_PATH)
        set_cache("active_tool", "", CODEBASE_EXPLORER_CACHE_PATH)


def dependencies_guardrail(hook_input: dict[str, Any]) -> None:
    is_todo_read = get_cache("is_todo_read", CODEBASE_EXPLORER_CACHE_PATH)
    hook_event_name = hook_input.get("hook_event_name", "")
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    set_cache("active_tool", tool_name, CODEBASE_EXPLORER_CACHE_PATH)

    if is_todo_read:
        print("Todo file already read.")
        return
    if hook_event_name != "PreToolUse":
        print("Invalid hook event name.")
        return

    if tool_name != "Read":
        block_response(
            f"Invalid tool name. Please read the todo file first in {TODO_FILE_PATH.absolute()}"
        )
    file_path = tool_input.get("file_path", "")
    if file_path != str(TODO_FILE_PATH.absolute()):
        block_response(
            f"Please read the todo file first in {TODO_FILE_PATH.absolute()}"
        )

    set_cache("is_todo_read", True, CODEBASE_EXPLORER_CACHE_PATH)
    print("Todo file read successfully.")


def file_write_guardrail(hook_input: dict[str, Any]) -> None:
    hook_event_name = hook_input.get("hook_event_name", "")
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    if tool_name != "Write" or hook_event_name != "PreToolUse":
        return
    file_path = tool_input.get("file_path", "")
    if file_path != str(REPORT_FILE_PATH.absolute()):
        block_response(
            "Invalid file path. Please write the report to the correct path."
        )

    set_cache("is_report_written", True, CODEBASE_EXPLORER_CACHE_PATH)
    print("Report written successfully.")


def _block_stoppage(hook_input: dict[str, Any]) -> None:
    hook_event_name = hook_input.get("hook_event_name", "")
    is_report_written = get_cache("is_report_written", CODEBASE_EXPLORER_CACHE_PATH)
    if hook_event_name != "Stop":
        return
    if not is_report_written:
        block_response("Report is not written. Please write the report first.")

    set_cache("is_codebase_explorer_done", True, SUBAGENTS_CACHE_PATH)
    set_cache("current_workflow_phase", "", MAIN_CACHE_PATH)
    print("Codebase explorer completed.")


def main() -> None:
    # hook_input = test_read_tool
    # hook_input = test_post_tool_use_input
    # hook_input = test_write_tool
    hook_input = test_stop_input
    set_tool_active(hook_input)
    dependencies_guardrail(hook_input)
    file_write_guardrail(hook_input)
    _block_stoppage(hook_input)
    set_tool_inactive(hook_input)


if __name__ == "__main__":
    main()
