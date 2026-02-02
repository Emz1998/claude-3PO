#!/usr/bin/env python3
"""Unified configuration loader for workflow orchestration.

Provides user-friendly YAML configuration with:
- Simple wildcard patterns (no regex knowledge required)
- Validation with actionable error messages
- Typed access via dataclasses
- Backward compatibility with existing JSON config
"""

import re
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

# Configuration file paths
CONFIG_DIR = Path(__file__).parent
YAML_CONFIG_PATH = CONFIG_DIR / "workflow.config.yaml"
JSON_CONFIG_PATH = CONFIG_DIR / "workflow_config.json"

# Module-level cache
_unified_config_cache: dict[str, Any] | None = None


# =============================================================================
# DATACLASSES
# =============================================================================


@dataclass
class ProjectConfig:
    """Project settings from configuration."""

    name: str = "Unnamed Project"
    version: str = "v0.1.0"
    target_release: str = ""


@dataclass
class FeaturesConfig:
    """Feature flags from configuration."""

    dry_run: bool = False
    strict_phase_order: bool = True
    require_deliverables: bool = True
    verbose_logging: bool = False


@dataclass
class FileDeliverable:
    """A file-based deliverable (read/write/edit)."""

    type: Literal["files"] = "files"
    action: Literal["read", "write", "edit"] = "read"
    pattern: str = ""
    regex_pattern: str = ""  # Converted from user-friendly pattern
    folder: str = ""
    file: str = ""
    description: str = ""
    priority: int | None = None
    extensions: list[str] = field(default_factory=list)


@dataclass
class CommandDeliverable:
    """A command-based deliverable (bash)."""

    type: Literal["commands"] = "commands"
    action: Literal["bash"] = "bash"
    command: str = ""
    description: str = ""
    allow_failure: bool = False
    priority: int | None = None


@dataclass
class SkillDeliverable:
    """A skill-based deliverable (invoke)."""

    type: Literal["skill"] = "skill"
    action: Literal["invoke"] = "invoke"
    name: str = ""
    pattern: str = ""
    description: str = ""
    priority: int | None = None


Deliverable = FileDeliverable | CommandDeliverable | SkillDeliverable


@dataclass
class PhaseDeliverables:
    """All deliverables for a phase."""

    read: list[FileDeliverable] = field(default_factory=list)
    write: list[FileDeliverable] = field(default_factory=list)
    edit: list[FileDeliverable] = field(default_factory=list)
    bash: list[CommandDeliverable] = field(default_factory=list)
    skill: list[SkillDeliverable] = field(default_factory=list)


@dataclass
class UnifiedWorkflowConfig:
    """Complete unified workflow configuration."""

    project: ProjectConfig = field(default_factory=ProjectConfig)
    phases: dict[str, list[str]] = field(default_factory=dict)
    agents: dict[str, str] = field(default_factory=dict)
    deliverables: dict[str, PhaseDeliverables] = field(default_factory=dict)
    required_read_order: list[str] = field(default_factory=list)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    environments: dict[str, dict[str, Any]] = field(default_factory=dict)


# =============================================================================
# PATTERN CONVERSION
# =============================================================================


def wildcard_to_regex(pattern: str) -> str:
    """Convert user-friendly wildcard pattern to regex.

    Supports:
    - * = any characters (except /)
    - ** = any path (including /)
    - ? = single character

    Examples:
        *.md -> [^/]*\\.md$
        **/*.ts -> .*[^/]*\\.ts$
        codebase-status_*.md -> codebase-status_[^/]*\\.md$
    """
    if not pattern:
        return ""

    # Escape regex special characters (except our wildcards)
    escaped = ""
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                # ** matches any path including /
                escaped += ".*"
                i += 2
                # Skip trailing / after **
                if i < len(pattern) and pattern[i] == "/":
                    i += 1
                continue
            else:
                # * matches any characters except /
                escaped += "[^/]*"
        elif char == "?":
            escaped += "."
        elif char in ".^$+{}[]|()\\":
            escaped += "\\" + char
        else:
            escaped += char
        i += 1

    # Anchor at end
    if not escaped.endswith("$"):
        escaped += "$"

    return escaped


def regex_to_wildcard(regex: str) -> str:
    """Convert regex pattern back to user-friendly wildcard (best effort).

    This is used for displaying patterns to users in error messages.
    """
    if not regex:
        return ""

    result = regex
    # Remove anchors
    result = result.rstrip("$")
    result = result.lstrip("^")

    # Convert common patterns
    result = result.replace(".*", "**")
    result = result.replace("[^/]*", "*")
    result = result.replace("\\.", ".")
    result = result.replace("\\/", "/")

    return result


# =============================================================================
# VALIDATION
# =============================================================================


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""

    pass


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate configuration and return list of issues.

    Returns:
        List of error messages. Empty list means valid.
    """
    issues: list[str] = []

    # Check required sections
    if "project" not in config:
        issues.append("Missing required section: 'project'")

    if "phases" not in config:
        issues.append("Missing required section: 'phases'")
    else:
        phases = config.get("phases", {})
        if "base" not in phases:
            issues.append("Missing required phase group: 'phases.base'")

    if "agents" not in config:
        issues.append("Missing required section: 'agents'")
    else:
        agents = config.get("agents", {})
        phases = config.get("phases", {})

        # Check all phases have agents assigned
        all_phases = set()
        for phase_group in phases.values():
            if isinstance(phase_group, list):
                all_phases.update(phase_group)

        for phase in all_phases:
            if phase not in agents and phase != "code":  # 'code' is a placeholder
                issues.append(
                    f"No agent assigned for phase '{phase}'. "
                    f"Add 'agents.{phase}: agent-name' to your configuration"
                )

    # Check deliverables patterns
    deliverables = config.get("deliverables", {})
    for phase_name, phase_deliverables in deliverables.items():
        if not isinstance(phase_deliverables, dict):
            continue

        for action in ["read", "write", "edit"]:
            items = phase_deliverables.get(action, [])
            if not isinstance(items, list):
                continue

            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    issues.append(
                        f"Invalid deliverable in '{phase_name}.{action}[{i}]': "
                        f"expected dict, got {type(item).__name__}"
                    )
                    continue

                # Check that pattern or file is specified
                if not item.get("pattern") and not item.get("file"):
                    issues.append(
                        f"Deliverable '{phase_name}.{action}[{i}]' must have "
                        f"either 'pattern' or 'file' specified"
                    )

    return issues


def format_validation_errors(issues: list[str]) -> str:
    """Format validation issues into user-friendly error message."""
    if not issues:
        return ""

    lines = [
        "=" * 60,
        "WORKFLOW CONFIGURATION ERROR",
        "=" * 60,
        "",
        "The following issues were found in workflow.config.yaml:",
        "",
    ]

    for i, issue in enumerate(issues, 1):
        lines.append(f"  {i}. {issue}")

    lines.extend(
        [
            "",
            "HOW TO FIX:",
            "  1. Open .claude/hooks/workflow/config/workflow.config.yaml",
            "  2. Address each issue listed above",
            "  3. Save the file and try again",
            "",
            "For help, see WORKFLOW_CONFIG_GUIDE.md",
            "=" * 60,
        ]
    )

    return "\n".join(lines)


# =============================================================================
# LOADING
# =============================================================================


def load_yaml_config(config_path: Path = YAML_CONFIG_PATH) -> dict[str, Any] | None:
    """Load configuration from YAML file.

    Returns:
        Configuration dictionary or None if file doesn't exist or yaml not available.
    """
    if yaml is None:
        return None

    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in {config_path}: {e}")


def load_json_config(config_path: Path = JSON_CONFIG_PATH) -> dict[str, Any] | None:
    """Load configuration from JSON file (legacy format).

    Returns:
        Configuration dictionary or None if file doesn't exist.
    """
    import json

    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Invalid JSON in {config_path}: {e}")


def convert_legacy_deliverables(
    legacy: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """Convert legacy deliverables format to new format.

    Legacy format:
        [{"type": "files", "action": "read", "pattern": ".*\\.md$"}]

    New format:
        {"read": [{"pattern": "*.md"}]}
    """
    result: dict[str, list[dict[str, Any]]] = {
        "read": [],
        "write": [],
        "edit": [],
        "bash": [],
        "skill": [],
    }

    for item in legacy:
        action = item.get("action", "read")
        pattern = item.get("pattern", "")

        # Convert regex to wildcard for display
        friendly_pattern = regex_to_wildcard(pattern)

        new_item: dict[str, Any] = {
            "pattern": friendly_pattern,
            "description": item.get("description", ""),
        }

        if item.get("priority"):
            new_item["priority"] = item["priority"]

        if action in result:
            result[action].append(new_item)

    return result


def parse_deliverable(
    item: dict[str, Any], action: str
) -> FileDeliverable | CommandDeliverable | SkillDeliverable | None:
    """Parse a single deliverable item into appropriate dataclass."""
    if action == "bash":
        return CommandDeliverable(
            command=item.get("command", ""),
            description=item.get("description", ""),
            allow_failure=item.get("allow_failure", False),
            priority=item.get("priority"),
        )

    if action == "skill":
        return SkillDeliverable(
            name=item.get("name", ""),
            pattern=item.get("pattern", ""),
            description=item.get("description", ""),
            priority=item.get("priority"),
        )

    # File-based deliverable
    pattern = item.get("pattern", "")
    file_path = item.get("file", "")

    # Build regex pattern
    if file_path:
        # Exact file match - allow any path prefix
        regex_pattern = ".*" + re.escape(file_path) + "$"
    elif pattern:
        # Wildcard pattern
        folder = item.get("folder", "")
        if folder:
            # Allow any path prefix, then folder/pattern
            full_pattern = f"**/{folder}/{pattern}"
        else:
            # Allow any path prefix
            full_pattern = f"**/{pattern}"
        regex_pattern = wildcard_to_regex(full_pattern)
    else:
        regex_pattern = ""

    return FileDeliverable(
        action=action,  # type: ignore
        pattern=pattern,
        regex_pattern=regex_pattern,
        folder=item.get("folder", ""),
        file=file_path,
        description=item.get("description", ""),
        priority=item.get("priority"),
        extensions=item.get("extensions", []),
    )


def parse_phase_deliverables(phase_data: dict[str, Any]) -> PhaseDeliverables:
    """Parse all deliverables for a phase."""
    result = PhaseDeliverables()

    for action in ["read", "write", "edit"]:
        items = phase_data.get(action, [])
        if not isinstance(items, list):
            continue

        parsed_list = []
        for item in items:
            if isinstance(item, dict):
                deliverable = parse_deliverable(item, action)
                if deliverable and isinstance(deliverable, FileDeliverable):
                    parsed_list.append(deliverable)

        setattr(result, action, parsed_list)

    # Parse bash commands
    bash_items = phase_data.get("bash", [])
    if isinstance(bash_items, list):
        result.bash = [
            d
            for d in (parse_deliverable(item, "bash") for item in bash_items if isinstance(item, dict))
            if d and isinstance(d, CommandDeliverable)
        ]

    # Parse skills
    skill_items = phase_data.get("skill", [])
    if isinstance(skill_items, list):
        result.skill = [
            d
            for d in (parse_deliverable(item, "skill") for item in skill_items if isinstance(item, dict))
            if d and isinstance(d, SkillDeliverable)
        ]

    return result


def load_unified_config(
    use_cache: bool = True, validate: bool = True, environment: str | None = None
) -> UnifiedWorkflowConfig:
    """Load unified workflow configuration.

    Tries YAML config first, falls back to JSON with deprecation warning.

    Args:
        use_cache: Whether to use cached configuration
        validate: Whether to validate configuration
        environment: Environment name for overrides (e.g., 'dev', 'prod')

    Returns:
        UnifiedWorkflowConfig dataclass instance

    Raises:
        ConfigurationError: If configuration is invalid
    """
    global _unified_config_cache

    if use_cache and _unified_config_cache is not None:
        return _build_config_from_dict(_unified_config_cache, environment)

    # Try YAML first
    config = load_yaml_config()

    if config is None:
        # Fall back to JSON with deprecation warning
        config = load_json_config()
        if config is not None:
            warnings.warn(
                "Using deprecated workflow_config.json. "
                "Please migrate to workflow.config.yaml for better usability.",
                DeprecationWarning,
                stacklevel=2,
            )

    if config is None:
        # Return defaults
        return UnifiedWorkflowConfig()

    # Validate if requested
    if validate:
        issues = validate_config(config)
        if issues:
            error_msg = format_validation_errors(issues)
            print(error_msg, file=sys.stderr)
            raise ConfigurationError(f"Configuration has {len(issues)} issue(s)")

    # Cache raw config
    _unified_config_cache = config

    return _build_config_from_dict(config, environment)


def _build_config_from_dict(
    config: dict[str, Any], environment: str | None = None
) -> UnifiedWorkflowConfig:
    """Build UnifiedWorkflowConfig from dictionary."""
    # Project settings
    project_data = config.get("project", {})
    project = ProjectConfig(
        name=project_data.get("name", "Unnamed Project"),
        version=project_data.get("version", "v0.1.0"),
        target_release=project_data.get("target_release", ""),
    )

    # Feature flags
    features_data = config.get("features", {})

    # Apply environment overrides if specified
    if environment:
        env_overrides = config.get("environments", {}).get(environment, {})
        env_features = env_overrides.get("features", {})
        features_data = {**features_data, **env_features}

    features = FeaturesConfig(
        dry_run=features_data.get("dry_run", False),
        strict_phase_order=features_data.get("strict_phase_order", True),
        require_deliverables=features_data.get("require_deliverables", True),
        verbose_logging=features_data.get("verbose_logging", False),
    )

    # Phases
    phases = config.get("phases", {})

    # Agents (support both 'agents' and legacy 'subagents')
    agents = config.get("agents", config.get("subagents", {}))

    # Deliverables
    deliverables_data = config.get("deliverables", {})
    deliverables: dict[str, PhaseDeliverables] = {}

    for phase_name, phase_data in deliverables_data.items():
        if isinstance(phase_data, list):
            # Legacy format - convert
            converted = convert_legacy_deliverables(phase_data)
            deliverables[phase_name] = parse_phase_deliverables(converted)
        elif isinstance(phase_data, dict):
            # New format
            deliverables[phase_name] = parse_phase_deliverables(phase_data)

    return UnifiedWorkflowConfig(
        project=project,
        phases=phases,
        agents=agents,
        deliverables=deliverables,
        required_read_order=config.get("required_read_order", []),
        features=features,
        environments=config.get("environments", {}),
    )


def clear_unified_cache() -> None:
    """Clear the unified configuration cache."""
    global _unified_config_cache
    _unified_config_cache = None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_project_settings() -> ProjectConfig:
    """Get project settings from configuration."""
    config = load_unified_config()
    return config.project


def get_feature_flags(environment: str | None = None) -> FeaturesConfig:
    """Get feature flags from configuration."""
    config = load_unified_config(environment=environment)
    return config.features


def get_agent_for_phase(phase: str) -> str | None:
    """Get the agent assigned to a phase."""
    config = load_unified_config()
    return config.agents.get(phase)


def get_phase_deliverables_typed(phase: str) -> PhaseDeliverables:
    """Get typed deliverables for a specific phase."""
    config = load_unified_config()
    return config.deliverables.get(phase, PhaseDeliverables())


def get_deliverable_patterns(phase: str, action: str) -> list[str]:
    """Get regex patterns for a specific phase and action.

    Args:
        phase: Phase name (e.g., 'explore')
        action: Action type ('read', 'write', 'edit')

    Returns:
        List of regex patterns for matching files
    """
    deliverables = get_phase_deliverables_typed(phase)
    items = getattr(deliverables, action, [])

    patterns = []
    for item in items:
        if isinstance(item, FileDeliverable) and item.regex_pattern:
            patterns.append(item.regex_pattern)

    return patterns


def is_file_allowed(file_path: str, phase: str, action: str) -> bool:
    """Check if a file path matches allowed patterns for phase/action.

    Args:
        file_path: Path to check
        phase: Current phase
        action: Action being performed ('read', 'write', 'edit')

    Returns:
        True if file matches any allowed pattern
    """
    patterns = get_deliverable_patterns(phase, action)

    if not patterns:
        return True  # No restrictions if no patterns defined

    for pattern in patterns:
        if re.search(pattern, file_path):
            return True

    return False


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================


def get_legacy_deliverables_format(phase: str) -> list[dict[str, str]]:
    """Get deliverables in legacy format for backward compatibility.

    Returns format compatible with existing code:
        [{"type": "files", "action": "read", "pattern": ".*\\.md$"}]
    """
    deliverables = get_phase_deliverables_typed(phase)
    result: list[dict[str, str]] = []

    for action in ["read", "write", "edit"]:
        items = getattr(deliverables, action, [])
        for item in items:
            if isinstance(item, FileDeliverable):
                legacy_item: dict[str, Any] = {
                    "type": "files",
                    "action": action,
                    "pattern": item.regex_pattern or item.pattern,
                }
                if item.priority is not None:
                    legacy_item["priority"] = item.priority
                result.append(legacy_item)

    return result


# =============================================================================
# CLI
# =============================================================================


if __name__ == "__main__":
    try:
        config = load_unified_config(validate=True)
        print("Configuration loaded successfully!")
        print(f"\nProject: {config.project.name}")
        print(f"Version: {config.project.version}")
        print(f"Target Release: {config.project.target_release}")
        print(f"\nPhases: {list(config.phases.keys())}")
        print(f"Agents: {len(config.agents)} configured")
        print(f"Deliverables: {len(config.deliverables)} phases")
        print(f"\nFeatures:")
        print(f"  - Dry run: {config.features.dry_run}")
        print(f"  - Strict phase order: {config.features.strict_phase_order}")
        print(f"  - Require deliverables: {config.features.require_deliverables}")
        print(f"  - Verbose logging: {config.features.verbose_logging}")
    except ConfigurationError as e:
        sys.exit(1)
