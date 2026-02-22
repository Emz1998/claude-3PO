#!/usr/bin/env python3
"""Configuration module for workflow orchestration.

Provides unified access to workflow configuration including phases,
deliverables, and subagent mappings via the unified YAML loader.
"""

from .unified_loader import (
    # Configuration classes
    UnifiedWorkflowConfig,
    ProjectConfig,
    FeaturesConfig,
    TriggerConfig,
    TriggersConfig,
    FileDeliverable,
    CommandDeliverable,
    SkillDeliverable,
    PhaseDeliverables,
    # Main loader
    load_unified_config,
    clear_unified_cache,
    # Convenience functions
    get_project_settings,
    get_feature_flags,
    get_triggers,
    get_agent_for_phase,
    get_phase_deliverables_typed,
    get_deliverable_patterns,
    is_file_allowed,
    # Pattern utilities
    wildcard_to_regex,
    regex_to_wildcard,
    # Validation
    ConfigurationError,
    validate_config,
    format_validation_errors,
)

__all__ = [
    "UnifiedWorkflowConfig",
    "ProjectConfig",
    "FeaturesConfig",
    "TriggerConfig",
    "TriggersConfig",
    "FileDeliverable",
    "CommandDeliverable",
    "SkillDeliverable",
    "PhaseDeliverables",
    "load_unified_config",
    "clear_unified_cache",
    "get_project_settings",
    "get_feature_flags",
    "get_triggers",
    "get_agent_for_phase",
    "get_phase_deliverables_typed",
    "get_deliverable_patterns",
    "is_file_allowed",
    "wildcard_to_regex",
    "regex_to_wildcard",
    "ConfigurationError",
    "validate_config",
    "format_validation_errors",
]
