"""bash_guard.py — Phase-based Bash command enforcement using flat state model."""

import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from build.config import PR_COMMAND_PATTERNS, TEST_RUN_PATTERNS, CI_CHECK_PATTERNS
from build.session_store import SessionStore

CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(feat|fix|chore|refactor|docs|test|style|perf|ci|build|revert)"
    r"(\(.+\))?"   # optional scope
    r"!?"           # optional breaking change indicator
    r": .+"         # colon + space + description
)


def is_pr_command(command: str) -> bool:
    return any(re.search(p, command) for p in PR_COMMAND_PATTERNS)


def is_test_run(command: str) -> bool:
    return any(re.search(p, command) for p in TEST_RUN_PATTERNS)


def is_ci_check(command: str) -> bool:
    return any(re.search(p, command) for p in CI_CHECK_PATTERNS)


def _extract_commit_message(command: str) -> str | None:
    """Extract the commit message from a git commit -m command.

    Returns None if the command is not a git commit with -m flag.
    """
    if not re.search(r"\bgit\s+commit\b", command):
        return None
    if not re.search(r"\s-m\s", command):
        return None

    # Handle heredoc-style: git commit -m "$(cat <<'EOF'\nmsg\nEOF\n)"
    heredoc_match = re.search(r"-m\s+[\"']\$\(cat\s+<<['\"]?EOF['\"]?\n(.+?)(?:\nEOF)", command, re.DOTALL)
    if heredoc_match:
        return heredoc_match.group(1).split("\n")[0].strip()

    # Handle simple: git commit -m 'msg' or git commit -m "msg"
    simple_match = re.search(r"""-m\s+(['"])(.*?)\1""", command)
    if simple_match:
        return simple_match.group(2).strip()

    return None


def validate_commit_format(command: str) -> tuple[str, str]:
    """Validate that git commit messages follow conventional commit format.

    Returns ("allow", "") if valid or not a git commit.
    Returns ("block", reason) if the commit message is invalid.
    """
    message = _extract_commit_message(command)
    if message is None:
        return "allow", ""

    # Take only the first line for validation
    first_line = message.split("\n")[0].strip()

    if not first_line or not CONVENTIONAL_COMMIT_RE.match(first_line):
        return "block", (
            "Blocked: commit message must follow conventional commit format: "
            "'type(scope): description'. Valid types: feat, fix, chore, refactor, "
            "docs, test, style, perf, ci, build, revert."
        )

    return "allow", ""


def validate_pre(hook_input: dict, store: SessionStore) -> tuple[str, str]:
    """Validate a Bash PreToolUse invocation.

    Blocks PR commands outside pr-create phase or without passing validation.
    Enforces conventional commit format on git commit commands.
    """
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    command = hook_input.get("tool_input", {}).get("command", "")

    # Commit message format enforcement
    result = validate_commit_format(command)
    if result[0] == "block":
        return result

    if not is_pr_command(command):
        return "allow", ""

    phase = state.get("phase", "")
    validation_result = state.get("validation_result")

    if phase != "pr-create":
        return "block", f"Blocked: PR commands are only allowed during 'pr-create' phase (current: '{phase}'). Complete validation first to advance."

    if validation_result != "Pass":
        return "block", "Blocked: cannot create PR -- validation has not passed yet. Run the QualityAssurance agent to get a 'Pass' result before creating the PR."

    return "allow", ""
