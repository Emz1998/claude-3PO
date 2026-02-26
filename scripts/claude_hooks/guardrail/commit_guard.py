#!/usr/bin/env python3
"""PreToolUse guard for /commit skill — builds conventional commit template."""

from pathlib import Path
from typing import Any

from scripts.claude_hooks.utils.hook import PreToolUse, Skill, Hook  # type: ignore
from scripts.claude_hooks.sprint.sprint import Sprint  # type: ignore

TEMPLATE_PATH = Path(__file__).parent / "templates" / "commit.md"
VALID_TYPES = {"feat", "fix", "refactor", "docs", "test", "chore", "style", "perf", "ci"}


class CommitGuard:
    """Intercepts `skill:commit` calls and injects a commit message template."""

    def __init__(self, hook_input: dict[str, Any]):
        self._hook = PreToolUse(**hook_input)
        self._sprint = Sprint.create()

    def run(self) -> None:
        if not isinstance(self._hook.tool_input, Skill):
            return
        if self._hook.tool_input.skill != "commit":
            return

        story_id = self._sprint.state.current_story
        if not story_id:
            self._hook.block("No active story. Start a story before committing.")
            return

        in_progress = self._sprint.task.get_task_in_progress()
        if not in_progress:
            self._hook.block("No tasks in progress. Log a task before committing.")
            return

        commit_type = self._parse_type()
        if commit_type is None:
            args = self._hook.tool_input.args or ""
            invalid = args.strip().split()[0] if args.strip() else ""
            sorted_types = sorted(VALID_TYPES)
            self._hook.block(
                f"Invalid commit type '{invalid}'. Use: {', '.join(sorted_types)}"
            )
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
        self._hook.success_response(
            f"Use this commit message format:\n\n{message}"
        )

    def _parse_type(self) -> str | None:
        """Extract commit type from args. Defaults to 'feat'. Returns None if invalid."""
        args = self._hook.tool_input.args
        if not args:
            return "feat"
        parts = args.strip().split()
        if not parts:
            return "feat"
        if parts[0] in VALID_TYPES:
            return parts[0]
        return None


if __name__ == "__main__":
    hook_input = Hook._read_stdin()
    CommitGuard(hook_input).run()
