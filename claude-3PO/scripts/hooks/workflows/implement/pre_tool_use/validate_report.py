"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from typing import Literal
from utils.hook import Hook  # type: ignore
from config import Config  # type: ignore
from pathlib import Path  # type: ignore
from lib.store import StateStore  # type: ignore
from typing import Any, cast, Callable  # type: ignore
from utils.run_pr_check import run_pr_view  # type: ignore
from lib.conformance_check import template_conformance_check  # type: ignore

CLAUDE_3PO_DIR = Path.cwd() / "claude-3PO"
PROJECT_DIR = Path.cwd()

REPORT_TEMPLATE = CLAUDE_3PO_DIR / "templates" / "report.md"
REPORT_FILE_PATH = PROJECT_DIR / "report.md"


def get_file_path(hook_input: dict[str, Any]) -> str:
    return hook_input.get("tool_input", {}).get("file_path", "")


def get_content(hook_input: dict[str, Any]) -> str:
    return hook_input.get("tool_input", {}).get("content", "")


def is_valid_file_path(file_path: str) -> bool:
    return file_path == REPORT_TEMPLATE


def is_valid_report(report: str) -> tuple[bool, str]:
    template = REPORT_TEMPLATE.read_text()
    ok, diff = template_conformance_check(template, report)
    return ok, diff


def main() -> None:
    hook_input = Hook.read_stdin()
    state = StateStore()

    current_phases = state.current_phases_names
    if "write-report" not in current_phases:
        return

    file_path = get_file_path(hook_input)
    if not is_valid_file_path(file_path):
        Hook.block("File path is not valid")
        return

    report = get_content(hook_input)
    valid_report, error = is_valid_report(report)
    if not valid_report:
        Hook.block(f"Report is not valid: \n{error}")
        return


if __name__ == "__main__":
    main()
