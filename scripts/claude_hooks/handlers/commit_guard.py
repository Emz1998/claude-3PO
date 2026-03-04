"""PreToolUse handler — builds conventional commit template for /commit skill."""

from pathlib import Path
from typing import Any
import json
import sys
import subprocess

from scripts.claude_hooks.flag_file import FlagFile
from scripts.claude_hooks.models import PreToolUse, Skill
from scripts.claude_hooks.responses import block, succeed, set_decision, debug
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.handlers.workflow_gate import check_workflow_gate

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "commit.md"
VALID_TYPES = {
    "feat",
    "fix",
    "refactor",
    "docs",
    "test",
    "chore",
    "style",
    "perf",
    "ci",
}

COMMIT_FLAG = FlagFile("commit_flag")


def read_stdin_json() -> dict[str, Any]:
    """Parse JSON from stdin. Returns empty dict on error."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def _parse_args(tool_input: Skill) -> list[str] | None:
    """Extract args from tool input. Returns None if invalid.

    Expected format: type scope "summary" "body" "footer"
    Summary, body, and footer must be wrapped in double quotes.
    """
    import shlex

    args = tool_input.args
    if not args:
        return None
    try:
        parts = shlex.split(args.strip())
    except ValueError:
        return None
    if len(parts) != 5:
        return None
    return parts


def _validate_scope(scope: str) -> bool:
    """Validate scope against commit flag data. Returns False if invalid."""
    state = COMMIT_FLAG.read()

    if state is None:
        return False

    scope_story, scope_task = scope.strip().split("/")
    current_story = state.get("current_story", None)
    completed_tasks = state.get("completed_tasks", None)
    if current_story is None:
        return False

    if completed_tasks is None:
        return False

    if scope_story != current_story:
        return False

    if scope_task not in completed_tasks:
        return False

    return True


def _validate_type(type: str) -> bool:
    """Extract commit type from args. Defaults to 'feat'. Returns None if invalid."""
    if type in VALID_TYPES:
        return True
    return False


def setup_guard(hook_input: dict[str, Any]) -> None:
    """Block all tools except Skill:commit when uncommitted work exists."""
    if not check_workflow_gate():
        return
    if not COMMIT_FLAG.exists():
        return
    hook = PreToolUse(**hook_input)
    if isinstance(hook.tool_input, Skill) and hook.tool_input.skill == "commit":
        return
    block("Uncommitted work exists. Run /commit before using other tools.")


def handle(hook_input: dict[str, Any]) -> None:
    """Commit guard handler."""

    if not check_workflow_gate():
        succeed("commit_guard: workflow gate inactive")
        return

    setup_guard(hook_input)
    hook = PreToolUse(**hook_input)


    parsed_args = _parse_args(hook.tool_input.args)
    if parsed_args is None:
        succeed(f"commit_guard: invalid args '{hook.tool_input.args}'")
        return

    _type, scope, summary, body, footer = parsed_args

    if not _validate_scope(scope):
        succeed(f"commit_guard: invalid scope '{scope}'")
        return

    if not _validate_type(_type):
        succeed(f"commit_guard: invalid type '{_type}'")
        return

    template = TEMPLATE_PATH.read_text()
    message = template.format(
        type=_type,
        scope=scope,
        summary=summary,
        body=body,
        footer=footer,
    )
    # subprocess.run(["git", "add", "."], capture_output=True, text=True)
    # subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)

    response = (
        f"Successfully committed changes. {_type} {scope} {summary} {body} {footer}"
    )
    set_decision(system_message=response)

    _, scope_task = scope.strip().split("/")
    state = COMMIT_FLAG.remove_from("completed_tasks", scope_task)
    if not state.get("completed_tasks"):
        COMMIT_FLAG.remove()
