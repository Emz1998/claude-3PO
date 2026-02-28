"""PreToolUse handler — builds conventional commit template for /commit skill."""

from pathlib import Path
from typing import Any

from scripts.claude_hooks.models import PreToolUse, Skill
from scripts.claude_hooks.responses import block, succeed
from scripts.claude_hooks.sprint.sprint import Sprint
from scripts.claude_hooks.handlers.workflow_gate import check_workflow_gate

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "commit.md"
VALID_TYPES = {"feat", "fix", "refactor", "docs", "test", "chore", "style", "perf", "ci"}


def _parse_type(tool_input: Skill) -> str | None:
    """Extract commit type from args. Defaults to 'feat'. Returns None if invalid."""
    args = tool_input.args
    if not args:
        return "feat"
    parts = args.strip().split()
    if not parts:
        return "feat"
    if parts[0] in VALID_TYPES:
        return parts[0]
    return None


def handle(hook_input: dict[str, Any]) -> None:
    """Commit guard handler."""
    if not check_workflow_gate():
        return
    hook = PreToolUse(**hook_input)
    if not isinstance(hook.tool_input, Skill):
        return
    if hook.tool_input.skill != "commit":
        return

    sprint = Sprint.create()

    story_id = sprint.state.current_story
    if not story_id:
        block("No active story. Start a story before committing.")
        return

    in_progress = sprint.task.get_task_in_progress()
    if not in_progress:
        block("No tasks in progress. Log a task before committing.")
        return

    commit_type = _parse_type(hook.tool_input)
    if commit_type is None:
        args = hook.tool_input.args or ""
        invalid = args.strip().split()[0] if args.strip() else ""
        sorted_types = sorted(VALID_TYPES)
        block(f"Invalid commit type '{invalid}'. Use: {', '.join(sorted_types)}")
        return

    scope = f"{story_id}/{'/'.join(in_progress)}"
    template = TEMPLATE_PATH.read_text()
    message = template.format(
        type=commit_type,
        scope=scope,
        summary="<summary>",
        body="<body>",
        footer="<footer>",
    )
    succeed(f"Use this commit message format:\n\n{message}")
