#!/usr/bin/env python3
"""Configuration loader for workflow orchestration.

Thin delegation layer to unified_loader.py. Preserves import paths
used by existing code while unified_loader handles actual loading.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .unified_loader import (
    load_unified_config,
    clear_unified_cache,
    wildcard_to_regex,
)

CONFIG_PATH = Path(__file__).parent / "workflow_config.json"
YAML_CONFIG_PATH = Path(__file__).parent / "workflow.config.yaml"


@dataclass
class Deliverable:
    """A single deliverable item."""

    type: Literal["files", "commands", "artifacts", "skill"]
    action: Literal["write", "read", "edit", "bash", "invoke"]
    pattern: str
    priority: int | None = None


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

    Delegates to unified_loader which handles YAML/JSON loading.
    Returns dict format for backward compatibility.
    """
    unified = load_unified_config(use_cache=use_cache, validate=False)

    # Convert unified config to legacy dict format
    deliverables: dict[str, Any] = {}
    for phase_name, phase_deliverables in unified.deliverables.items():
        phase_list: list[dict[str, Any]] = []
        for action in ["read", "write", "edit"]:
            items = getattr(phase_deliverables, action, [])
            for item in items:
                entry: dict[str, Any] = {
                    "type": "files",
                    "action": action,
                    "pattern": item.regex_pattern or item.pattern,
                }
                if item.priority is not None:
                    entry["priority"] = item.priority
                phase_list.append(entry)
        for item in phase_deliverables.bash:
            phase_list.append({
                "type": "commands",
                "action": "bash",
                "pattern": item.command,
                "allow_failure": item.allow_failure,
            })
        for item in phase_deliverables.skill:
            phase_list.append({
                "type": "skill",
                "action": "invoke",
                "pattern": item.name or item.pattern,
            })
        deliverables[phase_name] = phase_list

    return {
        "phases": unified.phases,
        "subagents": unified.agents,
        "deliverables": deliverables,
        "required_read_order": unified.required_read_order,
    }


def get_config() -> WorkflowConfig:
    """Get typed workflow configuration."""
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
    """Get complete phase order based on test strategy."""
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
    """Get deliverables configuration."""
    config = load_workflow_config()
    deliverables = config.get("deliverables", {})
    if phase is not None:
        return {phase: deliverables.get(phase, [])}
    return deliverables


def get_phase_deliverables(phase: str) -> list[dict[str, str]]:
    """Get deliverables for a specific phase."""
    config = load_workflow_config()
    return config.get("deliverables", {}).get(phase, [])


def get_phase_subagents() -> dict[str, str]:
    """Get phase to subagent mapping."""
    config = load_workflow_config()
    return config.get("subagents", {})


def get_subagent_for_phase(phase: str) -> str | None:
    """Get the subagent for a specific phase."""
    return get_phase_subagents().get(phase)


def get_required_read_order() -> list[str]:
    """Get the required file read order."""
    config = load_workflow_config()
    return config.get("required_read_order", [])


def clear_cache() -> None:
    """Clear the configuration cache."""
    clear_unified_cache()


if __name__ == "__main__":
    config = get_config()
    print(f"Phases: {config.phases}")
    print(f"Subagents: {config.subagents}")
    print(f"TDD order: {get_phases('tdd')}")
