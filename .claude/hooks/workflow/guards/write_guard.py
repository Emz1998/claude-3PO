"""write_guard.py — Phase-based file write enforcement using flat state model."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"

CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".swift",
    ".c",
    ".cpp",
    ".h",
    ".rb",
    ".sh",
}

TEST_PATH_PATTERNS = [
    re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)"),
    re.compile(r"(^|/)(test_.*|.*_test)\.(py|js|ts|jsx|tsx)$"),
    re.compile(r"(^|/).*\.(test|spec)\.(js|jsx|ts|tsx)$"),
]


def _get_file_path(hook_input: dict) -> str:
    tool_input = hook_input.get("tool_input", {})
    tool_response = hook_input.get("tool_response", {})
    return tool_input.get("file_path", "") or tool_response.get("filePath", "")


def _is_code_file(file_path: str) -> bool:
    return Path(file_path).suffix in CODE_EXTENSIONS


def _is_test_file(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/")
    return any(p.search(normalized) for p in TEST_PATH_PATTERNS)


def _is_claude_config(file_path: str) -> bool:
    return "/.claude/" in file_path or file_path.startswith(".claude/")


def _is_plan_file(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/")
    return ".claude/plans/" in normalized or normalized.startswith(".claude/plans/")


def _is_report_file(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/")
    return ".claude/reports/" in normalized or normalized.startswith(".claude/reports/")


def validate_pre(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Validate a Write/Edit tool invocation (PreToolUse).

    Returns ("allow", "") or ("block", reason).
    """
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    file_path = _get_file_path(hook_input)
    phase = state.get("phase", "")

    # Claude config files are always allowed
    if _is_claude_config(file_path):
        return "allow", ""

    # Non-code files are always allowed
    if not _is_code_file(file_path):
        return "allow", ""

    # Code file rules by phase:
    if phase in ("write-plan", "review"):
        if _is_plan_file(file_path):
            return "allow", ""
        return (
            "block",
            f"Code files may not be written during '{phase}' phase. Write plan to .claude/plans/ instead.",
        )

    if phase == "write-tests":
        if _is_test_file(file_path):
            return "allow", ""
        return (
            "block",
            "Only test files may be written during 'write-tests' phase. Write tests before implementation code.",
        )

    if phase == "write-code":
        return "allow", ""

    if phase in ("validate", "pr-create"):
        return "block", f"Cannot modify implementation files during '{phase}' phase."

    if phase == "ci-check":
        # Allow writes — PostToolUse will trigger regression
        return "allow", ""

    if phase == "report":
        if _is_report_file(file_path):
            return "allow", ""
        return (
            "block",
            "Only report files (.claude/reports/) may be written during 'report' phase.",
        )

    if phase in ("explore", "plan", "approved", "task-create"):
        return "block", f"Code files may not be written during '{phase}' phase."

    return "allow", ""


def handle_post(hook_input: dict, store: StateStore) -> tuple[str, str]:
    """Handle PostToolUse Write/Edit — track plan writes, test files, report writes."""
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    file_path = _get_file_path(hook_input)
    phase = state.get("phase", "")

    # Track all written files for read_guard's files_written constraint
    if file_path:

        def _track_written(s: dict) -> None:
            files = s.setdefault("files_written", [])
            if file_path not in files:
                files.append(file_path)

        store.update(_track_written)

    # Track plan file writes
    if _is_plan_file(file_path) and phase in ("write-plan", "review"):

        def _record_plan(s: dict) -> None:
            s["plan_file"] = file_path
            s["plan_written"] = True
            s["phase"] = "review"

        store.update(_record_plan)
        return "allow", ""

    # Track test file writes
    if _is_test_file(file_path) and phase == "write-tests" and _is_code_file(file_path):

        def _record_test(s: dict) -> None:
            files = s.setdefault("test_files_created", [])
            if file_path not in files:
                files.append(file_path)

        store.update(_record_test)
        return "allow", ""

    # Handle code writes in ci-check — trigger regression to write-code
    if (
        _is_code_file(file_path)
        and not _is_test_file(file_path)
        and phase == "ci-check"
    ):

        def _regress(s: dict) -> None:
            s["phase"] = "write-code"
            s["ci_status"] = "pending"
            s["ci_check_executed"] = False
            s["validation_result"] = None
            s["pr_status"] = "pending"

        store.update(_regress)
        return "allow", ""

    # Track report writes
    if _is_report_file(file_path) and phase == "report":

        def _complete_report(s: dict) -> None:
            s["report_written"] = True
            s["phase"] = "completed"

        store.update(_complete_report)
        return "allow", ""

    return "allow", ""


# Legacy: old guardrail.py calls validate() with a Path
def validate(hook_input: dict, state_path=None) -> tuple[str, str]:
    """Legacy compatibility shim for old guardrail.py."""
    store = StateStore(state_path or DEFAULT_STATE_PATH)
    return validate_pre(hook_input, store)
