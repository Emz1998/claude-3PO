"""Roadmap utilities for status loggers and workflow hooks."""

from .resolver import (
    resolve_milestones_and_phases,
    update_current_pointer,
    update_summary,
)
from .roadmap import (
    # Type aliases
    StatusType,
    CriteriaStatusType,
    TestStrategyType,
    # Path and loading utilities
    get_project_dir,
    get_prd_path,
    load_prd,
    get_current_version,
    get_roadmap_path,
    load_roadmap,
    save_roadmap,
    # Find utilities
    find_task_in_roadmap,
    find_ac_in_roadmap,
    find_sc_in_roadmap,
    find_milestone_in_roadmap,
    find_phase_in_roadmap,
    # Phase utilities
    is_checkpoint_phase,
    get_checkpoint_phases,
    # Milestone utilities
    get_milestone_mcp_servers,
    has_mcp_servers,
    # Task utilities
    get_task_test_strategy,
    is_tdd_task,
    is_ta_task,
    get_task_owner,
    is_parallel_task,
    # Criteria description utilities
    get_ac_description,
    get_sc_description,
    get_ac_with_description,
    get_sc_with_description,
    # Dependency and status utilities
    get_incomplete_task_deps,
    get_incomplete_milestone_deps,
    get_unmet_acs,
    get_unmet_scs,
    all_acs_met,
    all_scs_met,
    all_tasks_completed,
    any_task_in_progress,
    all_milestones_completed,
    any_milestone_in_progress,
    # Query utilities
    get_tdd_tasks,
    get_ta_tasks,
    get_parallel_tasks,
    get_sequential_tasks,
    get_milestone_tasks,
    # Context utilities
    get_task_context,
    get_milestone_context,
    get_phase_context,
    # Current pointer utilities
    get_current_task_id,
    get_current_milestone_id,
    get_current_milestone_full_name,
    get_current_phase_id,
    get_current_phase_full_name,
    get_current_task,
    get_current_milestone,
    get_current_phase,
    get_current_task_test_strategy,
)

__all__ = [
    # Type aliases
    "StatusType",
    "CriteriaStatusType",
    "TestStrategyType",
    # Path and loading utilities
    "get_project_dir",
    "get_prd_path",
    "load_prd",
    "get_current_version",
    "get_roadmap_path",
    "load_roadmap",
    "save_roadmap",
    # Find utilities
    "find_task_in_roadmap",
    "find_ac_in_roadmap",
    "find_sc_in_roadmap",
    "find_milestone_in_roadmap",
    "find_phase_in_roadmap",
    # Phase utilities
    "is_checkpoint_phase",
    "get_checkpoint_phases",
    # Milestone utilities
    "get_milestone_mcp_servers",
    "has_mcp_servers",
    # Task utilities
    "get_task_test_strategy",
    "is_tdd_task",
    "is_ta_task",
    "get_task_owner",
    "is_parallel_task",
    # Criteria description utilities
    "get_ac_description",
    "get_sc_description",
    "get_ac_with_description",
    "get_sc_with_description",
    # Dependency and status utilities
    "get_incomplete_task_deps",
    "get_incomplete_milestone_deps",
    "get_unmet_acs",
    "get_unmet_scs",
    "all_acs_met",
    "all_scs_met",
    "all_tasks_completed",
    "any_task_in_progress",
    "all_milestones_completed",
    "any_milestone_in_progress",
    # Resolution utilities
    "resolve_milestones_and_phases",
    "update_current_pointer",
    "update_summary",
    # Query utilities
    "get_tdd_tasks",
    "get_ta_tasks",
    "get_parallel_tasks",
    "get_sequential_tasks",
    "get_milestone_tasks",
    # Context utilities
    "get_task_context",
    "get_milestone_context",
    "get_phase_context",
    # Current pointer utilities
    "get_current_task_id",
    "get_current_milestone_id",
    "get_current_milestone_full_name",
    "get_current_phase_id",
    "get_current_phase_full_name",
    "get_current_task",
    "get_current_milestone",
    "get_current_phase",
    "get_current_task_test_strategy",
]
