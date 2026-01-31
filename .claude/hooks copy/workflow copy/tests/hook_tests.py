from typing import Any
from pathlib import Path
import sys
from datetime import datetime

# Add parent directory to import from utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.project import BASE_PATH  # type: ignore
from utils.cache import get_cache  # type: ignore

MAIN_CACHE_PATH = Path(".claude/hooks/states/main.json")

PROJECT_BASE_PATH = BASE_PATH
session_id = get_cache("session_id", MAIN_CACHE_PATH)


# REPORT_FILE_PATH
REPORT_FILE_PATH = (
    PROJECT_BASE_PATH
    / "codebase-status"
    / f"codebase-status_{session_id}_{datetime.now().strftime('%m%d%Y')}.md"
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
    "tool_input": "",
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
    "tool_name": "Bash",
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
