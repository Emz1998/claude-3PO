#!/usr/bin/env python3
"""Configuration module for workflow orchestration.

Provides unified access to workflow configuration including phases,
deliverables, and subagent mappings.

This module exports both legacy loader functions (for backward compatibility)
and new unified loader functions (recommended for new code).
"""

# Legacy loader (backward compatible)
from .loader import (
    WorkflowConfig,
    load_workflow_config,
    get_config,
    get_phases,
    get_deliverables,
    get_phase_subagents,
    get_phase_deliverables,
    clear_cache,
)

# Unified loader (recommended)
from .unified_loader import (
    # Configuration classes
    UnifiedWorkflowConfig,
    ProjectConfig,
    FeaturesConfig,
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
    # Backward compatibility
    get_legacy_deliverables_format,
)

__all__ = [
    # Legacy exports (backward compatible)
    "WorkflowConfig",
    "load_workflow_config",
    "get_config",
    "get_phases",
    "get_deliverables",
    "get_phase_subagents",
    "get_phase_deliverables",
    "clear_cache",
    # Unified exports (recommended)
    "UnifiedWorkflowConfig",
    "ProjectConfig",
    "FeaturesConfig",
    "FileDeliverable",
    "CommandDeliverable",
    "SkillDeliverable",
    "PhaseDeliverables",
    "load_unified_config",
    "clear_unified_cache",
    "get_project_settings",
    "get_feature_flags",
    "get_agent_for_phase",
    "get_phase_deliverables_typed",
    "get_deliverable_patterns",
    "is_file_allowed",
    "wildcard_to_regex",
    "regex_to_wildcard",
    "ConfigurationError",
    "validate_config",
    "format_validation_errors",
    "get_legacy_deliverables_format",
]
