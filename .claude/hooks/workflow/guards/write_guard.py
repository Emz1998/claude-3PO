"""write_guard.py — Phase-based file write enforcement using flat state model."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.config import CODE_EXTENSIONS, TEST_PATH_PATTERNS
from workflow.session_store import SessionStore


def get_file_path(hook_input: dict) -> str:
    tool_input = hook_input.get("tool_input", {})
    tool_response = hook_input.get("tool_response", {})
    return tool_input.get("file_path", "") or tool_response.get("filePath", "")


def is_code_file(file_path: str) -> bool:
    return Path(file_path).suffix in CODE_EXTENSIONS


def is_test_file(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/")
    return any(p.search(normalized) for p in TEST_PATH_PATTERNS)


def is_claude_config(file_path: str) -> bool:
    return "/.claude/" in file_path or file_path.startswith(".claude/")


def is_plan_file(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/")
    return ".claude/plans/" in normalized or normalized.startswith(".claude/plans/")


def is_report_file(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/")
    return ".claude/reports/" in normalized or normalized.startswith(".claude/reports/")


def validate_plan_template(content: str) -> list[str]:
    """Return list of missing required sections in plan content."""
    required = {
        "Context": re.compile(r"^##\s+Context", re.MULTILINE | re.IGNORECASE),
        "Approach": re.compile(r"^##\s+(Approach|Steps)", re.MULTILINE | re.IGNORECASE),
        "Files to Modify": re.compile(
            r"^##\s+Files to Modify", re.MULTILINE | re.IGNORECASE
        ),
        "Verification": re.compile(r"^##\s+Verification", re.MULTILINE | re.IGNORECASE),
    }
    return [name for name, pattern in required.items() if not pattern.search(content)]


def _get_plan_content(hook_input: dict) -> str:
    """Get the resulting plan content for Write or Edit tool."""
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name == "Write":
        return tool_input.get("content", "")

    # Edit: read file, apply replacement in memory
    file_path = get_file_path(hook_input)
    try:
        current = Path(file_path).read_text()
    except (FileNotFoundError, OSError):
        return ""
    old_string = tool_input.get("old_string", "")
    new_string = tool_input.get("new_string", "")
    return current.replace(old_string, new_string)


def validate_pre(hook_input: dict, store: SessionStore) -> tuple[str, str]:
    """Validate a Write/Edit tool invocation (PreToolUse).

    Returns ("allow", "") or ("block", reason).
    """
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    file_path = get_file_path(hook_input)
    phase = state.get("phase", "")

    # Plan file template enforcement during write-plan/review
    if phase in ("write-plan", "review") and is_plan_file(file_path):
        content = _get_plan_content(hook_input)
        missing = validate_plan_template(content)
        if missing:
            return (
                "block",
                f"Blocked: plan missing required sections: {', '.join(missing)}. Add them before saving.",
            )
        return "allow", ""

    # write-plan/review: only plan files allowed (block everything else)
    if phase in ("write-plan", "review"):
        return (
            "block",
            f"Blocked: only plan files (.claude/plans/) may be written during '{phase}' phase.",
        )

    # Report phase: only report files allowed
    if phase == "report":
        if is_report_file(file_path):
            return "allow", ""
        return (
            "block",
            f"Blocked: cannot write '{file_path}' during 'report' phase. Write the completion report to .claude/reports/latest-report.md instead.",
        )

    # Claude config files are always allowed
    if is_claude_config(file_path):
        return "allow", ""

    # Non-code files are always allowed
    if not is_code_file(file_path):
        return "allow", ""

    if phase == "write-tests":
        if is_test_file(file_path):
            return "allow", ""
        return (
            "block",
            "Blocked: only test files may be written during 'write-tests' phase. Write tests before implementation code.",
        )

    if phase == "write-code":
        return "allow", ""

    if phase in ("validate", "pr-create"):
        return (
            "block",
            f"Blocked: cannot modify implementation files during '{phase}' phase. Complete validation before making changes.",
        )

    if phase == "ci-check":
        # Allow writes — PostToolUse will trigger regression
        return "allow", ""

    if phase in ("explore", "plan", "present-plan", "task-create"):
        match phase:
            case "explore":
                return (
                    "block",
                    "Blocked: cannot write to files during 'explore' phase. Complete exploration before writing to files.",
                )
            case "plan":
                return (
                    "block",
                    "Blocked: cannot write to files during 'plan' phase. Complete plan before writing to files.",
                )
            case "present-plan":
                return (
                    "block",
                    "Blocked: cannot write to files during 'present-plan' phase. Complete plan presentation before writing to files.",
                )
            case "task-create":
                return (
                    "block",
                    "Blocked: cannot write to files during 'task-create' phase. Complete task creation before writing to files.",
                )

    return "allow", ""
