#!/usr/bin/env python3
"""
Consolidated guardrail for all subagents.

Single entry point for all subagent-specific tool restrictions.
Uses a registry pattern to configure per-subagent guardrails.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (  # type: ignore
    GuardrailConfig,
    GuardrailRunner,
    block_response,
    get_cache,
    load_cache,
    write_cache,
    read_stdin_json,
    create_directory_validator,
    create_session_file_validator,
    create_pattern_validator,
    create_extension_blocker,
    get_current_version,
    get_roadmap_path,
    load_roadmap,
    find_task_in_roadmap,
)

# Test file patterns for test-engineer
TEST_FILE_PATTERNS = [
    r"\.test\.(ts|tsx|js|jsx)$",
    r"\.spec\.(ts|tsx|js|jsx)$",
    r"test_.*\.py$",
    r".*_test\.py$",
    r"conftest\.py$",
    r"/__tests__/",
    r"/tests/",
    r"/test/",
    r"^tests/",
    r"^test/",
    r"^__tests__/",
]

# Engineer agents that require task status checking
ENGINEER_AGENTS = {
    "backend-engineer",
    "frontend-engineer",
    "fullstack-developer",
    "html-prototyper",
    "react-prototyper",
    "test-engineer",
}

# Guardrail configurations registry
GUARDRAIL_CONFIGS: dict[str, GuardrailConfig] = {
    "code-reviewer": GuardrailConfig(
        target_subagent="code-reviewer",
        cache_key="code_reviewer_guardrail_active",
        guarded_tools={"Write", "Edit"},
        path_validator=create_session_file_validator("revisions", "revisions"),
    ),
    "codebase-explorer": GuardrailConfig(
        target_subagent="codebase-explorer",
        cache_key="codebase_explorer_guardrail_active",
        guarded_tools={"Write", "Edit"},
        path_validator=create_session_file_validator("codebase-status", "codebase-status"),
    ),
    "fullstack-developer": GuardrailConfig(
        target_subagent="fullstack-developer",
        cache_key="fullstack_developer_guardrail_active",
        guarded_tools={"Write", "Edit"},
        path_validator=create_extension_blocker(".md", except_files=["README.md"]),
    ),
    "gemini-manager": GuardrailConfig(
        target_subagent="gemini-manager",
        cache_key="gemini_manager_guardrail_active",
        guarded_tools={"Write", "Edit"},
        blocked_skills_except={"discuss:gemini"},
        path_validator=create_directory_validator("decisions"),
    ),
    "gpt-manager": GuardrailConfig(
        target_subagent="gpt-manager",
        cache_key="gpt_manager_guardrail_active",
        guarded_tools={"Write", "Edit"},
        blocked_skills_except={"discuss:gpt"},
        path_validator=create_directory_validator("decisions"),
    ),
    "plan-consultant": GuardrailConfig(
        target_subagent="plan-consultant",
        cache_key="plan_consultant_guardrail_active",
        guarded_tools={"Write", "Edit"},
        path_validator=create_directory_validator("decisions"),
    ),
    "planning-specialist": GuardrailConfig(
        target_subagent="planning-specialist",
        cache_key="planner_guardrail_active",
        guarded_tools={"Write", "Edit"},
        path_validator=create_session_file_validator("plans", "plan"),
    ),
    "project-manager": GuardrailConfig(
        target_subagent="project-manager",
        cache_key="project_manager_guardrail_active",
        blocked_tools={"Write", "Edit"},
        allowed_skills={"log:ac", "log:sc", "log:task"},
    ),
    "test-engineer": GuardrailConfig(
        target_subagent="test-engineer",
        cache_key="test_engineer_guardrail_active",
        guarded_tools={"Write", "Edit"},
        path_validator=create_pattern_validator(
            TEST_FILE_PATTERNS,
            allow_match=True,
            error_msg="Only test files allowed (*.test.ts, *.spec.ts, __tests__/, tests/)",
        ),
    ),
    "version-manager": GuardrailConfig(
        target_subagent="version-manager",
        cache_key="version_manager_guardrail_active",
        blocked_tools={"Write", "Edit", "MultiEdit"},
        block_unsafe_bash=True,
    ),
}


def get_current_task_status() -> tuple[str | None, str | None]:
    """Get current task ID and status from roadmap. Returns (task_id, status)."""
    version = get_current_version()
    if not version:
        return None, None

    roadmap_path = get_roadmap_path(version)
    roadmap = load_roadmap(roadmap_path)
    if not roadmap:
        return None, None

    current = roadmap.get("current", {})
    task_id = current.get("task")
    if not task_id:
        return None, None

    _, _, task = find_task_in_roadmap(roadmap, task_id)
    if not task:
        return task_id, None

    return task_id, task.get("status", "not_started")


def is_build_active() -> bool:
    """Check if /build skill is currently active."""
    return get_cache("build_skill_active") is True


class ConsolidatedGuardrailRunner:
    """Unified runner that handles all subagent guardrails."""

    ACTIVE_SUBAGENT_KEY = "active_subagent"
    ENGINEER_ACTIVE_KEY = "engineer_task_logger_guardrail_active"

    def get_active_subagent(self) -> str | None:
        """Get the currently active subagent type."""
        return get_cache(self.ACTIVE_SUBAGENT_KEY)

    def get_active_config(self) -> GuardrailConfig | None:
        """Get config for the currently active subagent."""
        subagent = self.get_active_subagent()
        if subagent and subagent in GUARDRAIL_CONFIGS:
            return GUARDRAIL_CONFIGS[subagent]
        return None

    def activate(self, subagent_type: str) -> None:
        """Activate guardrail for a subagent (only one at a time)."""
        cache = load_cache()
        cache[self.ACTIVE_SUBAGENT_KEY] = subagent_type
        write_cache(cache)

    def deactivate(self) -> None:
        """Deactivate the current subagent guardrail."""
        cache = load_cache()
        cache[self.ACTIVE_SUBAGENT_KEY] = None
        write_cache(cache)

    def is_engineer_agent_active(self) -> bool:
        """Check if an engineer agent guardrail is active."""
        return get_cache(self.ENGINEER_ACTIVE_KEY) is True

    def activate_engineer_guardrail(self) -> None:
        cache = load_cache()
        cache[self.ENGINEER_ACTIVE_KEY] = True
        write_cache(cache)

    def deactivate_engineer_guardrail(self) -> None:
        cache = load_cache()
        cache[self.ENGINEER_ACTIVE_KEY] = False
        write_cache(cache)

    def handle_task_pretool(self, input_data: dict) -> None:
        """Activate guardrail when matching subagent is spawned."""
        tool_input = input_data.get("tool_input", {})
        subagent_type = tool_input.get("subagent_type", "")

        # Activate guardrail for this subagent (replaces any previous)
        if subagent_type in GUARDRAIL_CONFIGS:
            self.activate(subagent_type)

        # Check if this is an engineer agent
        if subagent_type in ENGINEER_AGENTS:
            self.activate_engineer_guardrail()

    def handle_tool_pretool(self, input_data: dict) -> None:
        """Handle PreToolUse for the active guardrail."""
        config = self.get_active_config()

        # Check engineer task status first (applies to engineer agents)
        if self.is_engineer_agent_active():
            self.check_engineer_task_status(input_data)

        if not config:
            return

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Block completely blocked tools
        if tool_name in config.blocked_tools:
            block_response(
                f"GUARDRAIL: {tool_name} blocked for {config.target_subagent}."
            )

        # Handle Skill tool restrictions
        if tool_name == "Skill":
            skill_name = tool_input.get("skill", "")
            if config.allowed_skills is not None:
                if skill_name not in config.allowed_skills:
                    block_response(
                        f"GUARDRAIL: Skill blocked for {config.target_subagent}. "
                        f"Only {config.allowed_skills} allowed. Attempted: {skill_name}"
                    )
            elif config.blocked_skills_except is not None:
                if skill_name not in config.blocked_skills_except:
                    block_response(
                        f"GUARDRAIL: Skill blocked for {config.target_subagent}. "
                        f"Only '{config.blocked_skills_except}' allowed. Attempted: {skill_name}"
                    )

        # Handle Bash tool with unsafe command blocking
        if tool_name == "Bash" and config.block_unsafe_bash:
            from utils import is_safe_git_command  # type: ignore
            command = tool_input.get("command", "")
            if not is_safe_git_command(command):
                block_response(
                    f"GUARDRAIL: Bash command blocked for {config.target_subagent}. "
                    f"Only safe git commands allowed. Attempted: {command[:100]}"
                )

        # Handle guarded tools with path validation
        if tool_name in config.guarded_tools:
            file_path = tool_input.get("file_path", "")
            if config.path_validator:
                allowed, reason = config.path_validator(file_path)
                if not allowed:
                    block_response(
                        f"GUARDRAIL: {tool_name} blocked for {config.target_subagent}. {reason}"
                    )

    def check_engineer_task_status(self, input_data: dict) -> None:
        """Block tools if current task isn't in_progress for engineer agents."""
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Allow log:task skill to pass through
        if tool_name == "Skill":
            skill_name = tool_input.get("skill", "")
            if skill_name == "log:task":
                return

        # Check current task status from roadmap
        task_id, status = get_current_task_status()

        if status != "in_progress":
            block_response(
                f"GUARDRAIL: {tool_name} blocked. "
                f"Current task '{task_id}' must be 'in_progress' first (current: '{status}'). "
                "Use: /log:task <task-id> in_progress"
            )

    def handle_subagent_stop(self, input_data: dict) -> None:
        """Handle SubagentStop event."""
        # Deactivate the current subagent guardrail
        self.deactivate()

        # Handle engineer guardrail - check if task is completed
        if self.is_engineer_agent_active():
            task_id, status = get_current_task_status()

            if status != "completed":
                # Block stoppage with exit code 2
                block_response(
                    f"GUARDRAIL: Cannot stop. Task '{task_id}' must be 'completed' first "
                    f"(current: '{status}'). Use: /log:task <task-id> completed"
                )

            self.deactivate_engineer_guardrail()

    def run(self) -> None:
        input_data = read_stdin_json()
        if not input_data:
            sys.exit(0)

        # Only run guardrails when /build skill is active
        if not is_build_active():
            sys.exit(0)

        hook_event = input_data.get("hook_event_name", "")
        tool_name = input_data.get("tool_name", "")

        if hook_event == "PreToolUse":
            if tool_name == "Task":
                self.handle_task_pretool(input_data)
            else:
                self.handle_tool_pretool(input_data)
        elif hook_event == "SubagentStop":
            self.handle_subagent_stop(input_data)

        sys.exit(0)


if __name__ == "__main__":
    ConsolidatedGuardrailRunner().run()
