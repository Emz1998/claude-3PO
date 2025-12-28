#!/usr/bin/env python3
"""
Simplified subagent guardrail.

Enforces tool restrictions and path validation per subagent type.
Uses a declarative registry pattern for easy configuration.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (  # type: ignore
    block_response,
    get_cache,
    load_cache,
    write_cache,
    read_stdin_json,
    create_directory_validator,
    create_session_file_validator,
    create_pattern_validator,
    create_extension_blocker,
    is_safe_git_command,
)

# Test file patterns
TEST_PATTERNS = [
    r"\.(test|spec)\.(ts|tsx|js|jsx)$",
    r"(test_.*|.*_test)\.py$",
    r"conftest\.py$",
    r"(__tests__|tests?)/",
]

# Subagent configurations: {name: {blocked_tools, guarded_tools, path_validator, ...}}
CONFIGS: dict = {
    "code-reviewer": {
        "guarded": {"Write", "Edit"},
        "validator": create_session_file_validator("revisions", "revisions"),
    },
    "codebase-explorer": {
        "guarded": {"Write", "Edit"},
        "validator": create_session_file_validator("codebase-status", "codebase-status"),
    },
    "fullstack-developer": {
        "guarded": {"Write", "Edit"},
        "validator": create_extension_blocker(".md", except_files=["README.md"]),
    },
    "gemini-manager": {
        "guarded": {"Write", "Edit"},
        "validator": create_directory_validator("decisions"),
        "skills_allowed": {"discuss:gemini"},
    },
    "gpt-manager": {
        "guarded": {"Write", "Edit"},
        "validator": create_directory_validator("decisions"),
        "skills_allowed": {"discuss:gpt"},
    },
    "plan-consultant": {
        "guarded": {"Write", "Edit"},
        "validator": create_directory_validator("decisions"),
    },
    "planner": {
        "guarded": {"Write", "Edit"},
        "validator": create_session_file_validator("plans", "plan"),
    },
    "project-manager": {
        "blocked": {"Write", "Edit"},
        "skills_allowed": {"log:ac", "log:sc", "log:task"},
    },
    "test-engineer": {
        "guarded": {"Write", "Edit"},
        "validator": create_pattern_validator(
            TEST_PATTERNS,
            allow_match=True,
            error_msg="Only test files allowed (*.test.ts, *.spec.ts, __tests__/, tests/)",
        ),
    },
    "version-manager": {
        "blocked": {"Write", "Edit", "MultiEdit"},
        "safe_bash_only": True,
    },
}

CACHE_KEY = "active_subagent"


def get_active() -> str | None:
    """Get currently active subagent."""
    return get_cache(CACHE_KEY)


def activate(subagent: str) -> None:
    """Activate guardrail for subagent."""
    cache = load_cache()
    cache[CACHE_KEY] = subagent
    write_cache(cache)


def deactivate() -> None:
    """Deactivate current guardrail."""
    cache = load_cache()
    cache[CACHE_KEY] = None
    write_cache(cache)


def is_build_active() -> bool:
    """Check if /build skill is active."""
    return get_cache("build_skill_active") is True


def check_tool(subagent: str, config: dict, tool: str, tool_input: dict) -> None:
    """Check if tool is allowed for subagent."""
    # Completely blocked tools
    if tool in config.get("blocked", set()):
        block_response(f"GUARDRAIL: {tool} blocked for {subagent}.")

    # Skill restrictions
    if tool == "Skill":
        allowed = config.get("skills_allowed")
        if allowed is not None:
            skill = tool_input.get("skill", "")
            if skill not in allowed:
                block_response(
                    f"GUARDRAIL: Skill '{skill}' blocked for {subagent}. "
                    f"Allowed: {allowed}"
                )

    # Safe bash only
    if tool == "Bash" and config.get("safe_bash_only"):
        cmd = tool_input.get("command", "")
        if not is_safe_git_command(cmd):
            block_response(
                f"GUARDRAIL: Bash blocked for {subagent}. "
                f"Only safe git commands allowed."
            )

    # Guarded tools with path validation
    if tool in config.get("guarded", set()):
        validator = config.get("validator")
        if validator:
            file_path = tool_input.get("file_path", "")
            allowed, reason = validator(file_path)
            if not allowed:
                block_response(f"GUARDRAIL: {tool} blocked for {subagent}. {reason}")


def main() -> None:
    """Main entry point."""
    input_data = read_stdin_json()
    if not input_data:
        sys.exit(0)

    # Only run when /build is active
    if not is_build_active():
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if hook_event == "PreToolUse":
        # Task tool spawns subagent - activate guardrail
        if tool_name == "Task":
            subagent = tool_input.get("subagent_type", "")
            if subagent in CONFIGS:
                activate(subagent)
        else:
            # Check active guardrail for other tools
            subagent = get_active()
            if subagent and subagent in CONFIGS:
                check_tool(subagent, CONFIGS[subagent], tool_name, tool_input)

    elif hook_event == "SubagentStop":
        # Clean up on subagent stop
        deactivate()

    sys.exit(0)


if __name__ == "__main__":
    main()
