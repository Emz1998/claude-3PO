#!/usr/bin/env python3
"""Base guardrail utilities for subagent hooks."""

import re
import sys
from datetime import datetime
from typing import Callable

from .cache import get_cache, load_cache, write_cache
from .input import read_stdin_json
from .output import block_response
from .roadmap import (
    get_current_version,
    get_roadmap_path,
    load_roadmap,
    find_milestone_in_roadmap,
)
from .blockers import is_safe_git_command


def get_folder_name(item_id: str, item_name: str) -> str:
    """Get folder name in format ID_description (e.g., PH-001_phase-name)."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", item_name.lower()).strip("-")
    return f"{item_id}_{slug}"


def get_milestone_folder_name(roadmap: dict, milestone_id: str) -> str | None:
    """Get milestone folder name in format MS-NNN_description."""
    _, milestone = find_milestone_in_roadmap(roadmap, milestone_id)
    if not milestone:
        return None
    ms_id = milestone.get("id", "")
    ms_name = milestone.get("name", "")
    if not ms_id:
        return None
    return get_folder_name(ms_id, ms_name)


def get_phase_folder_name(roadmap: dict, phase_id: str) -> str | None:
    """Get phase folder name in format PH-NNN_description."""
    phases = roadmap.get("phases", [])
    for phase in phases:
        if phase.get("id") == phase_id:
            ph_id = phase.get("id", "")
            ph_name = phase.get("name", "")
            if not ph_id:
                return None
            return get_folder_name(ph_id, ph_name)
    return None


def get_milestone_context() -> tuple[str, str, str, str] | tuple[None, None, None, str]:
    """Get version, phase folder, milestone folder, and session_id. Returns error message if any."""
    version = get_current_version()
    if not version:
        return None, None, None, "Could not determine current version"

    roadmap_path = get_roadmap_path(version)
    roadmap = load_roadmap(roadmap_path)
    if not roadmap:
        return None, None, None, f"Could not load roadmap from {roadmap_path}"

    current = roadmap.get("current", {})
    phase_id = current.get("phase")
    milestone_id = current.get("milestone")

    if not phase_id:
        return None, None, None, "No current phase set in roadmap"
    if not milestone_id:
        return None, None, None, "No current milestone set in roadmap"

    phase_folder = get_phase_folder_name(roadmap, phase_id)
    if not phase_folder:
        return None, None, None, f"Could not find phase {phase_id}"

    milestone_folder = get_milestone_folder_name(roadmap, milestone_id)
    if not milestone_folder:
        return None, None, None, f"Could not find milestone {milestone_id}"

    session_id = get_cache("session_id") or ""
    if not session_id:
        return None, None, None, "No session_id in cache"

    return version, phase_folder, milestone_folder, session_id


class GuardrailConfig:
    """Configuration for a guardrail."""

    def __init__(
        self,
        target_subagent: str,
        cache_key: str,
        guarded_tools: set[str] | None = None,
        blocked_tools: set[str] | None = None,
        allowed_skills: set[str] | None = None,
        blocked_skills_except: set[str] | None = None,
        path_validator: Callable[[str], tuple[bool, str]] | None = None,
        block_unsafe_bash: bool = False,
    ):
        self.target_subagent = target_subagent
        self.cache_key = cache_key
        self.guarded_tools = guarded_tools or set()
        self.blocked_tools = blocked_tools or set()
        self.allowed_skills = allowed_skills
        self.blocked_skills_except = blocked_skills_except
        self.path_validator = path_validator
        self.block_unsafe_bash = block_unsafe_bash


class GuardrailRunner:
    """Runs guardrail logic based on configuration."""

    def __init__(self, config: GuardrailConfig):
        self.config = config

    def is_active(self) -> bool:
        return get_cache(self.config.cache_key) is True

    def activate(self) -> None:
        cache = load_cache()
        cache[self.config.cache_key] = True
        write_cache(cache)

    def deactivate(self) -> None:
        cache = load_cache()
        cache[self.config.cache_key] = False
        write_cache(cache)

    def handle_task_pretool(self, input_data: dict) -> None:
        tool_input = input_data.get("tool_input", {})
        subagent_type = tool_input.get("subagent_type", "")
        if subagent_type == self.config.target_subagent:
            self.activate()

    def handle_tool_pretool(self, input_data: dict) -> None:
        if not self.is_active():
            return

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Block completely blocked tools
        if tool_name in self.config.blocked_tools:
            block_response(
                f"GUARDRAIL: {tool_name} blocked for {self.config.target_subagent}."
            )

        # Handle Skill tool restrictions
        if tool_name == "Skill":
            skill_name = tool_input.get("skill", "")
            if self.config.allowed_skills is not None:
                if skill_name not in self.config.allowed_skills:
                    block_response(
                        f"GUARDRAIL: Skill blocked for {self.config.target_subagent}. "
                        f"Only {self.config.allowed_skills} allowed. Attempted: {skill_name}"
                    )
            elif self.config.blocked_skills_except is not None:
                if skill_name not in self.config.blocked_skills_except:
                    block_response(
                        f"GUARDRAIL: Skill blocked for {self.config.target_subagent}. "
                        f"Only '{self.config.blocked_skills_except}' allowed. Attempted: {skill_name}"
                    )
            return

        # Handle Bash tool with unsafe command blocking
        if tool_name == "Bash" and self.config.block_unsafe_bash:
            command = tool_input.get("command", "")
            if not is_safe_git_command(command):
                block_response(
                    f"GUARDRAIL: Bash command blocked for {self.config.target_subagent}. "
                    f"Only safe git commands allowed. Attempted: {command[:100]}"
                )

        # Handle guarded tools with path validation
        if tool_name in self.config.guarded_tools:
            file_path = tool_input.get("file_path", "")
            if self.config.path_validator:
                allowed, reason = self.config.path_validator(file_path)
                if not allowed:
                    block_response(
                        f"GUARDRAIL: {tool_name} blocked for {self.config.target_subagent}. {reason}"
                    )

    def handle_subagent_stop(self) -> None:
        if self.is_active():
            self.deactivate()

    def run(self) -> None:
        input_data = read_stdin_json()
        if not input_data:
            sys.exit(0)

        hook_event = input_data.get("hook_event_name", "")
        tool_name = input_data.get("tool_name", "")

        if hook_event == "PreToolUse":
            if tool_name == "Task":
                self.handle_task_pretool(input_data)
            else:
                self.handle_tool_pretool(input_data)
        elif hook_event == "SubagentStop":
            self.handle_subagent_stop()

        sys.exit(0)


# Path validator factories
def create_directory_validator(
    subfolder: str,
) -> Callable[[str], tuple[bool, str]]:
    """Create a validator that allows writes to a specific milestone subfolder."""

    def validator(file_path: str) -> tuple[bool, str]:
        version, phase_folder, milestone_folder, error_or_session = get_milestone_context()
        if version is None:
            return False, error_or_session

        allowed_path = f"project/{version}/{phase_folder}/{milestone_folder}/{subfolder}/"
        if allowed_path in file_path:
            return True, ""
        return False, f"Only allowed path: {allowed_path}"

    return validator


def create_session_file_validator(
    subfolder: str, file_prefix: str
) -> Callable[[str], tuple[bool, str]]:
    """Create a validator for session-specific files with date pattern."""

    def validator(file_path: str) -> tuple[bool, str]:
        version, phase_folder, milestone_folder, error_or_session = get_milestone_context()
        if version is None:
            return False, error_or_session

        session_id = error_or_session
        date_pattern = r"\d{4}-\d{2}-\d{2}"
        version_escaped = re.escape(version)
        phase_escaped = re.escape(phase_folder)
        milestone_escaped = re.escape(milestone_folder)
        session_escaped = re.escape(session_id)

        pattern = (
            rf"project/{version_escaped}/{phase_escaped}/"
            rf"{milestone_escaped}/{subfolder}/"
            rf"{file_prefix}_{date_pattern}_{session_escaped}\.md$"
        )

        if re.search(pattern, file_path):
            return True, ""

        today = datetime.now().strftime("%Y-%m-%d")
        expected = (
            f"project/{version}/{phase_folder}/{milestone_folder}/{subfolder}/"
            f"{file_prefix}_{today}_{session_id}.md"
        )
        return False, f"Expected: {expected}"

    return validator


def create_pattern_validator(
    patterns: list[str], allow_match: bool = True, error_msg: str = ""
) -> Callable[[str], tuple[bool, str]]:
    """Create a validator based on regex patterns."""

    def validator(file_path: str) -> tuple[bool, str]:
        for pattern in patterns:
            if re.search(pattern, file_path):
                if allow_match:
                    return True, ""
                else:
                    return False, error_msg
        if allow_match:
            return False, error_msg
        return True, ""

    return validator


def create_extension_blocker(
    blocked_ext: str, except_files: list[str] | None = None
) -> Callable[[str], tuple[bool, str]]:
    """Create a validator that blocks specific extensions except for listed files."""
    except_files = except_files or []

    def validator(file_path: str) -> tuple[bool, str]:
        if not file_path.endswith(blocked_ext):
            return True, ""

        from pathlib import Path

        filename = Path(file_path).name.lower()
        if any(f.lower() == filename for f in except_files):
            return True, ""

        return False, f"Files with {blocked_ext} extension blocked except {except_files}"

    return validator
