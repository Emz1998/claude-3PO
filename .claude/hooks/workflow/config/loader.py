#!/usr/bin/env python3
"""Configuration loader for workflow orchestration.

Provides typed access to workflow configuration with caching.

NOTE: This module now delegates to unified_loader.py for configuration loading.
The JSON config is kept for backward compatibility but YAML is preferred.
"""

import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import json

CONFIG_PATH = Path(__file__).parent / "workflow_config.json"
YAML_CONFIG_PATH = Path(__file__).parent / "workflow.config.yaml"

# Module-level cache
_config_cache: dict[str, Any] | None = None
_using_yaml: bool = False


@dataclass
class Deliverable:
    """A single deliverable item."""

    type: Literal["files", "commands", "artifacts", "skill"]
    action: Literal["write", "read", "edit", "bash", "invoke"]
    pattern: str
    priority: int | None = None  # None = lowest priority (last)


@dataclass
class WorkflowConfig:
    """Typed workflow configuration."""

    phases: dict[str, list[str]] = field(default_factory=dict)
    subagents: dict[str, str] = field(default_factory=dict)
    deliverables: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    required_read_order: list[str] = field(default_factory=list)


def load_workflow_config(
    config_path: Path = CONFIG_PATH, use_cache: bool = True
) -> dict[str, Any]:
    """Load and cache workflow configuration.

    Tries YAML config first (workflow.config.yaml), falls back to JSON
    (workflow_config.json) with a deprecation warning.

    Args:
        config_path: Path to the JSON configuration file (for backward compat)
        use_cache: Whether to use cached config

    Returns:
        Configuration dictionary
    """
    global _config_cache, _using_yaml

    if use_cache and _config_cache is not None:
        return _config_cache

    default_config: dict[str, Any] = {
        "phases": {"base": [], "tdd": [], "test-after": []},
        "subagents": {},
        "deliverables": {},
        "required_read_order": [],
    }

    # Try YAML config first
    if YAML_CONFIG_PATH.exists():
        try:
            import yaml

            with open(YAML_CONFIG_PATH) as f:
                data = yaml.safe_load(f)

            if data:
                # Convert YAML format to expected format
                converted = _convert_yaml_to_internal(data)
                _config_cache = converted
                _using_yaml = True
                return converted
        except ImportError:
            pass  # yaml not installed, fall through to JSON
        except Exception:
            pass  # YAML parse error, fall through to JSON

    # Fall back to JSON
    if not config_path.exists():
        return default_config

    try:
        with open(config_path) as f:
            data = json.load(f)

        if YAML_CONFIG_PATH.exists():
            warnings.warn(
                "Using deprecated workflow_config.json. "
                "YAML config exists but failed to load. Check workflow.config.yaml.",
                DeprecationWarning,
                stacklevel=2,
            )
        elif not _using_yaml:
            warnings.warn(
                "Using deprecated workflow_config.json. "
                "Please migrate to workflow.config.yaml for better usability. "
                "See WORKFLOW_CONFIG_GUIDE.md for migration instructions.",
                DeprecationWarning,
                stacklevel=2,
            )
    except (json.JSONDecodeError, IOError):
        return default_config

    if not data:
        return default_config

    _config_cache = data
    return data


def _convert_yaml_to_internal(yaml_data: dict[str, Any]) -> dict[str, Any]:
    """Convert YAML config format to internal format expected by existing code.

    YAML format uses 'agents' and user-friendly deliverables.
    Internal format uses 'subagents' and regex patterns.
    """
    from .unified_loader import wildcard_to_regex

    result: dict[str, Any] = {
        "phases": yaml_data.get("phases", {}),
        "subagents": yaml_data.get("agents", yaml_data.get("subagents", {})),
        "deliverables": {},
        "required_read_order": yaml_data.get("required_read_order", []),
    }

    # Convert deliverables from YAML format to internal format
    yaml_deliverables = yaml_data.get("deliverables", {})

    for phase_name, phase_data in yaml_deliverables.items():
        if not isinstance(phase_data, dict):
            result["deliverables"][phase_name] = []
            continue

        internal_deliverables: list[dict[str, Any]] = []

        for action in ["read", "write", "edit"]:
            items = phase_data.get(action, [])
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue

                pattern = item.get("pattern", "")
                file_path = item.get("file", "")
                folder = item.get("folder", "")

                # Build regex pattern
                if file_path:
                    regex_pattern = file_path.replace(".", "\\.") + "$"
                elif pattern:
                    if folder:
                        full_pattern = f".*{folder}/{pattern}"
                    else:
                        full_pattern = f".*{pattern}"
                    regex_pattern = wildcard_to_regex(full_pattern)
                else:
                    continue

                internal_item: dict[str, Any] = {
                    "type": "files",
                    "action": action,
                    "pattern": regex_pattern,
                }

                if item.get("priority") is not None:
                    internal_item["priority"] = item["priority"]

                internal_deliverables.append(internal_item)

        # Handle bash commands
        bash_items = phase_data.get("bash", [])
        if isinstance(bash_items, list):
            for item in bash_items:
                if isinstance(item, dict):
                    internal_deliverables.append({
                        "type": "commands",
                        "action": "bash",
                        "pattern": item.get("command", ""),
                        "allow_failure": item.get("allow_failure", False),
                    })

        # Handle skills
        skill_items = phase_data.get("skill", [])
        if isinstance(skill_items, list):
            for item in skill_items:
                if isinstance(item, dict):
                    internal_deliverables.append({
                        "type": "skill",
                        "action": "invoke",
                        "pattern": item.get("name", item.get("pattern", "")),
                    })

        result["deliverables"][phase_name] = internal_deliverables

    return result


def get_config() -> WorkflowConfig:
    """Get typed workflow configuration.

    Returns:
        WorkflowConfig dataclass instance
    """
    data = load_workflow_config()
    return WorkflowConfig(
        phases=data.get("phases", {}),
        subagents=data.get("subagents", {}),
        deliverables=data.get("deliverables", {}),
        required_read_order=data.get("required_read_order", []),
    )


def get_phases(
    strategy: Literal["tdd", "test-after", "none"] = "tdd"
) -> list[str]:
    """Get complete phase order based on test strategy.

    Args:
        strategy: The testing strategy to use
            - "tdd": Full workflow with write-test before write-code
            - "test-after": Full workflow with write-code before write-test
            - "none": Simple 4-phase workflow (explore, plan, execute, commit)

    Returns:
        Complete list of phases in execution order
    """
    config = load_workflow_config()
    phases = config.get("phases", {})

    if strategy == "none":
        return phases.get("simple", ["explore", "plan", "execute", "commit"])

    base = phases.get("base", [])

    if "code" not in base:
        return base

    code_idx = base.index("code")
    before = base[:code_idx]
    after = base[code_idx + 1:]

    if strategy == "tdd":
        return before + phases.get("tdd", []) + after
    if strategy == "test-after":
        return before + phases.get("test-after", []) + after

    return before + after


def get_deliverables(phase: str | None = None) -> dict[str, list[dict[str, str]]]:
    """Get deliverables configuration.

    Args:
        phase: Optional phase to filter by

    Returns:
        Deliverables dictionary (all or for specific phase)
    """
    config = load_workflow_config()
    deliverables = config.get("deliverables", {})

    if phase is not None:
        return {phase: deliverables.get(phase, [])}

    return deliverables


def get_phase_deliverables(phase: str) -> list[dict[str, str]]:
    """Get deliverables for a specific phase.

    Args:
        phase: The phase name

    Returns:
        List of deliverable dictionaries for the phase
    """
    config = load_workflow_config()
    return config.get("deliverables", {}).get(phase, [])


def get_phase_subagents() -> dict[str, str]:
    """Get phase to subagent mapping.

    Returns:
        Dictionary mapping phase names to subagent names
    """
    config = load_workflow_config()
    return config.get("subagents", {})


def get_subagent_for_phase(phase: str) -> str | None:
    """Get the subagent for a specific phase.

    Args:
        phase: The phase name

    Returns:
        Subagent name or None if not found
    """
    subagents = get_phase_subagents()
    return subagents.get(phase)


def get_required_read_order() -> list[str]:
    """Get the required file read order.

    Returns:
        List of file names in required read order
    """
    config = load_workflow_config()
    return config.get("required_read_order", [])


def clear_cache() -> None:
    """Clear the configuration cache."""
    global _config_cache, _using_yaml
    _config_cache = None
    _using_yaml = False


if __name__ == "__main__":
    config = get_config()
    print(f"Phases: {config.phases}")
    print(f"Subagents: {config.subagents}")
    print(f"TDD order: {get_phases('tdd')}")
