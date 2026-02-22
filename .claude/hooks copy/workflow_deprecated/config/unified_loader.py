#!/usr/bin/env python3
"""Unified configuration loader for workflow orchestration.

Provides user-friendly YAML configuration with:
- Simple wildcard patterns (no regex knowledge required)
- Validation with actionable error messages
- Typed access via dataclasses
"""

import re
import sys
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
    filepath: str = ""  # New: replaces folder/pattern/file
    regex_pattern: str = ""  # Computed from filepath after placeholder resolution
    description: str = ""
    match: str | None = None
    strict_order: int | None = None
    extensions: list[str] = field(default_factory=list)


@dataclass
class CommandDeliverable:
    """A command-based deliverable (bash)."""

    type: Literal["commands"] = "commands"
    action: Literal["bash"] = "bash"
    command: str = ""
    description: str = ""
    match: str | None = None
    allow_failure: bool = False
    strict_order: int | None = None


@dataclass
class SkillDeliverable:
    """A skill-based deliverable (invoke)."""

    type: Literal["skill"] = "skill"
    action: Literal["invoke"] = "invoke"
    name: str = ""
    pattern: str = ""
    description: str = ""
    match: str | None = None
    strict_order: int | None = None


Deliverable = FileDeliverable | CommandDeliverable | SkillDeliverable


@dataclass
class TriggerConfig:
    """Configuration for a single trigger command."""

    command: str = ""
    arg_pattern: str = ""
    arg_hint: str = ""
    description: str = ""


@dataclass
class TriggersConfig:
    """Configuration for all trigger commands."""

    implement: TriggerConfig = field(
        default_factory=lambda: TriggerConfig(
            command="/implement",
            arg_pattern=r"MS-\d{3}$",
            arg_hint="MS-NNN",
        )
    )
    deactivate: TriggerConfig = field(
        default_factory=lambda: TriggerConfig(command="/deactivate-workflow")
    )
    dry_run: TriggerConfig = field(
        default_factory=lambda: TriggerConfig(command="/dry-run")
    )
    troubleshoot: TriggerConfig = field(
        default_factory=lambda: TriggerConfig(command="/troubleshoot")
    )


@dataclass
class BypassPhaseConfig:
    """Configuration for a bypass phase."""

    can_bypass: list[str] = field(default_factory=list)
    cannot_bypass: list[str] = field(default_factory=list)


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
    triggers: TriggersConfig = field(default_factory=TriggersConfig)
    agents: dict[str, str] = field(default_factory=dict)
    deliverables: dict[str, PhaseDeliverables] = field(default_factory=dict)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    bypass_phases: dict[str, BypassPhaseConfig] = field(default_factory=dict)


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


def resolve_filepath_placeholders(filepath: str) -> str:
    """Resolve {project} and {session} placeholders in filepath.

    Args:
        filepath: Path string potentially containing placeholders

    Returns:
        Resolved path string with placeholders replaced

    Placeholders:
        {project} -> project/v0.1.0/EPIC-002/FEAT-003 (current version/epic/feature path)
        {session} -> 1ab7b734 (current session ID)
    """
    if not filepath:
        return filepath

    result = filepath

    # Resolve {project} placeholder
    if "{project}" in result:
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from release_plan.project import get_feature_path  # type: ignore

            project_path = str(get_feature_path())
            # Validate path has real values (not empty components)
            if (
                project_path
                and "//" not in project_path
                and project_path != "project//"
            ):
                result = result.replace("{project}", project_path)
            else:
                # Fallback: remove placeholder, keep rest generic
                result = result.replace("{project}/", "")
        except (ImportError, Exception):
            result = result.replace("{project}/", "")

    # Resolve {session} placeholder
    if "{session}" in result:
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from utils.cache import get_session_id  # type: ignore

            session_id = get_session_id()
            if session_id:
                result = result.replace("{session}", session_id)
            else:
                # Fallback: replace with wildcard
                result = result.replace("{session}", "*")
        except (ImportError, Exception):
            result = result.replace("{session}", "*")

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

                # Check that filepath, pattern, or file is specified
                has_filepath = bool(item.get("filepath"))
                has_pattern = bool(item.get("pattern"))
                has_file = bool(item.get("file"))
                if not has_filepath and not has_pattern and not has_file:
                    issues.append(
                        f"Deliverable '{phase_name}.{action}[{i}]' must have "
                        f"'filepath', 'pattern', or 'file' specified"
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


def parse_deliverable(
    item: dict[str, Any], action: str
) -> FileDeliverable | CommandDeliverable | SkillDeliverable | None:
    """Parse a single deliverable item into appropriate dataclass."""
    if action == "bash":
        return CommandDeliverable(
            command=item.get("command", ""),
            description=item.get("description", ""),
            match=item.get("match"),
            allow_failure=item.get("allow_failure", False),
            strict_order=item.get("strict_order"),
        )

    if action == "skill":
        return SkillDeliverable(
            name=item.get("name", ""),
            pattern=item.get("pattern", ""),
            description=item.get("description", ""),
            match=item.get("match"),
            strict_order=item.get("strict_order"),
        )

    # File-based deliverable
    filepath = item.get("filepath", "")

    # Backward compatibility: build filepath from folder/pattern/file if present
    if not filepath:
        folder = item.get("folder", "")
        pattern = item.get("pattern", "")
        file_path = item.get("file", "")
        if file_path:
            filepath = file_path
        elif folder and pattern:
            filepath = f"{folder}/{pattern}"
        elif pattern:
            filepath = pattern

    # Resolve placeholders ({project}, {session})
    resolved_filepath = resolve_filepath_placeholders(filepath)

    # Convert to regex
    if resolved_filepath:
        if resolved_filepath.startswith("./"):
            # Exact match from repo root - strip ./ and anchor at start
            exact_path = resolved_filepath[2:]
            regex_pattern = "^" + wildcard_to_regex(exact_path)
        else:
            # Match anywhere in path
            regex_pattern = wildcard_to_regex(f"**/{resolved_filepath}")
    else:
        regex_pattern = ""

    return FileDeliverable(
        action=action,  # type: ignore
        filepath=filepath,  # Store original for display
        regex_pattern=regex_pattern,  # Resolved + converted to regex
        description=item.get("description", ""),
        match=item.get("match"),
        strict_order=item.get("strict_order"),
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
            for d in (
                parse_deliverable(item, "bash")
                for item in bash_items
                if isinstance(item, dict)
            )
            if d and isinstance(d, CommandDeliverable)
        ]

    # Parse skills
    skill_items = phase_data.get("skill", [])
    if isinstance(skill_items, list):
        result.skill = [
            d
            for d in (
                parse_deliverable(item, "skill")
                for item in skill_items
                if isinstance(item, dict)
            )
            if d and isinstance(d, SkillDeliverable)
        ]

    return result


def load_unified_config(
    use_cache: bool = True, validate: bool = True
) -> UnifiedWorkflowConfig:
    """Load unified workflow configuration from YAML.

    Args:
        use_cache: Whether to use cached configuration
        validate: Whether to validate configuration

    Returns:
        UnifiedWorkflowConfig dataclass instance

    Raises:
        ConfigurationError: If configuration is invalid
    """
    global _unified_config_cache

    if use_cache and _unified_config_cache is not None:
        return _build_config_from_dict(_unified_config_cache)

    config = load_yaml_config()

    if config is None:
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

    return _build_config_from_dict(config)


def _build_config_from_dict(config: dict[str, Any]) -> UnifiedWorkflowConfig:
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
    features = FeaturesConfig(
        dry_run=features_data.get("dry_run", False),
        strict_phase_order=features_data.get("strict_phase_order", True),
        require_deliverables=features_data.get("require_deliverables", True),
        verbose_logging=features_data.get("verbose_logging", False),
    )

    # Phases
    phases = config.get("phases", {})

    # Triggers
    triggers_data = config.get("triggers", {})
    triggers = TriggersConfig()
    for trigger_name in ("implement", "deactivate", "dry_run", "troubleshoot"):
        trigger_data = triggers_data.get(trigger_name, {})
        if isinstance(trigger_data, dict) and trigger_data:
            trigger = TriggerConfig(
                command=trigger_data.get("command", ""),
                arg_pattern=trigger_data.get("arg_pattern", ""),
                arg_hint=trigger_data.get("arg_hint", ""),
                description=trigger_data.get("description", ""),
            )
            setattr(triggers, trigger_name, trigger)

    # Agents (support both 'agents' and legacy 'subagents')
    agents = config.get("agents", config.get("subagents", {}))

    # Deliverables
    deliverables_data = config.get("deliverables", {})
    deliverables: dict[str, PhaseDeliverables] = {}

    for phase_name, phase_data in deliverables_data.items():
        if isinstance(phase_data, dict):
            deliverables[phase_name] = parse_phase_deliverables(phase_data)

    # Bypass phases
    bypass_data = config.get("bypass_phases", {})
    bypass_phases: dict[str, BypassPhaseConfig] = {}
    for bypass_name, bypass_config in bypass_data.items():
        if isinstance(bypass_config, dict):
            bypass_phases[bypass_name] = BypassPhaseConfig(
                can_bypass=bypass_config.get("can_bypass", []),
                cannot_bypass=bypass_config.get("cannot_bypass", []),
            )

    return UnifiedWorkflowConfig(
        project=project,
        phases=phases,
        triggers=triggers,
        agents=agents,
        deliverables=deliverables,
        features=features,
        bypass_phases=bypass_phases,
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


def get_feature_flags() -> FeaturesConfig:
    """Get feature flags from configuration."""
    config = load_unified_config()
    return config.features


def get_triggers() -> TriggersConfig:
    """Get trigger commands configuration."""
    config = load_unified_config()
    return config.triggers


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


def get_bypass_phases() -> dict[str, BypassPhaseConfig]:
    """Get bypass phases configuration.

    Returns:
        Dictionary mapping bypass phase names to their config
    """
    config = load_unified_config()
    return config.bypass_phases


def is_bypass_phase(phase: str) -> bool:
    """Check if a phase is a bypass phase.

    Args:
        phase: Phase name to check

    Returns:
        True if phase is a bypass phase
    """
    bypass_phases = get_bypass_phases()
    return phase in bypass_phases


def get_bypass_config(phase: str) -> BypassPhaseConfig | None:
    """Get bypass configuration for a phase.

    Args:
        phase: Phase name

    Returns:
        BypassPhaseConfig or None if not a bypass phase
    """
    bypass_phases = get_bypass_phases()
    return bypass_phases.get(phase)


def can_bypass_from(bypass_phase: str, current_phase: str) -> bool:
    """Check if a bypass phase can be entered from current phase.

    Args:
        bypass_phase: The bypass phase to enter
        current_phase: The current phase

    Returns:
        True if bypass is allowed from current phase
    """
    config = get_bypass_config(bypass_phase)
    if config is None:
        return False

    # Cannot bypass from phases in cannot_bypass list
    if current_phase in config.cannot_bypass:
        return False

    # Can bypass from phases in can_bypass list
    return current_phase in config.can_bypass


# =============================================================================
# CLI
# =============================================================================


def normalize_skill_name(skill: str) -> str:
    """Strip 'workflow:' prefix from skill name if present.

    Examples:
        "workflow:explore" → "explore"
        "explore" → "explore"
    """
    if skill.startswith("workflow:"):
        return skill[9:]  # len("workflow:") == 9
    return skill


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
