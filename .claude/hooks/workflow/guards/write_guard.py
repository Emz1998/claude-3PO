"""Write guard — blocks code file writes before plan is approved (and tests if TDD)."""

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


def validate(hook_input: dict, state_path: Path | None = None) -> tuple[str, str]:
    """Validate a Write/Edit tool invocation against the current workflow state.

    Returns ("allow", "") or ("block", reason).
    """
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Non-code files are always allowed
    if Path(file_path).suffix not in CODE_EXTENSIONS:
        return "allow", ""

    # Files inside .claude/ are config/hooks — always allowed
    if "/.claude/" in file_path or file_path.startswith(".claude/"):
        return "allow", ""

    path = state_path or DEFAULT_STATE_PATH
    store = StateStore(path)
    state = store.load()

    if not state.get("workflow_active", False):
        return "allow", ""

    phases: list[dict] = state.get("phases", [])
    phase_map = {p["name"]: p for p in phases}

    plan_status = phase_map.get("plan", {}).get("status", "pending")
    if plan_status != "completed":
        return "block", "Cannot write code before plan is approved"

    if state.get("TDD", False):
        tests_status = phase_map.get("write-tests", {}).get("status", "pending")
        if tests_status != "completed":
            return "block", "TDD enabled: write tests before implementation"

    return "allow", ""
