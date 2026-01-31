#!/usr/bin/env python3
"""Common blocking utilities for hook guards."""

import re
from typing import Callable

from .output import block_response


# Code file extensions
CODE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".html", ".py")

# Safe git command patterns (whitelist approach)
SAFE_GIT_PATTERNS = [
    r"^git\s+status\b",
    r"^git\s+log\b",
    r"^git\s+diff\b",
    r"^git\s+branch\b",
    r"^git\s+show\b",
    r"^git\s+ls-files\b",
    r"^git\s+rev-parse\b",
    r"^git\s+remote\b",
    r"^git\s+config\b",
    r"^git\s+fetch\b",
    r"^git\s+pull\b",
    r"^git\s+add\b",
    r"^git\s+commit\b",
    r"^git\s+push\b",
    r"^git\s+checkout\b",
    r"^git\s+switch\b",
    r"^git\s+merge\b",
    r"^git\s+rebase\b",
    r"^git\s+tag\b",
    r"^git\s+stash\b",
    r"^git\s+cherry-pick\b",
    r"^git\s+reset\b",
    r"^git\s+restore\b",
    r"^git\s+clean\b",
    r"^git\s+describe\b",
    r"^git\s+shortlog\b",
    r"^git\s+blame\b",
    r"^git\s+grep\b",
]


def is_code_file(file_path: str) -> bool:
    """Check if file is a code file based on extension."""
    return file_path.endswith(CODE_EXTENSIONS)


def is_safe_git_command(command: str) -> bool:
    """Check if command is a safe git operation."""
    if not command:
        return False
    command = command.strip()
    for pattern in SAFE_GIT_PATTERNS:
        if re.match(pattern, command, re.IGNORECASE):
            return True
    return False


def block_coding(file_path: str, reason: str) -> None:
    """Block coding operations on code files."""
    if is_code_file(file_path):
        block_response(reason)


def block_commit(command: str, reason: str) -> None:
    """Block git commit commands."""
    if "git commit" in command:
        block_response(reason)


def block_file_pattern(file_path: str, pattern: str, reason: str) -> None:
    """Block operations on files matching a pattern."""
    if pattern in file_path:
        block_response(reason)


def block_tool(tool_name: str, blocked_tools: set[str], reason: str) -> None:
    """Block specific tools entirely."""
    if tool_name in blocked_tools:
        block_response(reason)


def block_unsafe_bash(command: str, reason: str) -> None:
    """Block bash commands that are not safe git operations."""
    if not is_safe_git_command(command):
        block_response(reason)


def create_phase_blocker(phase: str, action: str) -> Callable[[str, str | None], None]:
    """Create a blocker function for a specific phase and action."""
    reason = f"You are not allowed to {action} in {phase} phase."

    def blocker(file_path: str, valid_pattern: str | None = None) -> None:
        if valid_pattern and valid_pattern in file_path:
            block_response(reason)
        elif not valid_pattern:
            block_response(reason)

    return blocker
