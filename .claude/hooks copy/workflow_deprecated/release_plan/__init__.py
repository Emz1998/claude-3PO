#!/usr/bin/env python3
"""Release plan state management module.

Provides state management for project release plans with:
- State loading/saving
- Getters for all state properties
- Setters for all state properties
- Checkers for completion status
- Resolvers for state transitions
"""

# Core state operations
from .state import (
    load_project_state,
    save_project_state,
    initialize_project_state,
)

# Getters
from .getters import (
    get_project_name,
    get_target_release,
    get_current_version,
    get_current_epic_id,
    get_current_feature_id,
    get_current_user_story,
    get_current_tasks,
    get_current_tasks_ids,
    get_current_task_dependencies,
    get_current_acs,
    get_current_acs_ids,
    get_current_scs,
    get_current_scs_ids,
    get_current_allowed_tasks,
    get_completed_tasks,
    get_completed_user_stories,
    get_completed_features,
    get_completed_epics,
    get_met_acs,
    get_met_scs,
    get_tasks_with_completed_deps,
)

# Checkers
from .checkers import (
    is_task_completed,
    is_ac_met,
    is_sc_met,
    is_user_story_completed,
    is_feature_completed,
    is_epic_completed,
    are_task_deps_completed,
    is_task_allowed,
    find_tasks_allowed_in_user_story,
)

# Setters (from new_setters to avoid circular imports)
from .new_setters import (
    set_project_name,
    set_target_release,
    set_current_version,
    set_current_epic_id,
    set_current_feature_id,
    set_current_user_story,
    set_current_user_story_status,
    set_current_tasks,
    set_current_acs,
    set_current_scs,
    set_current_allowed_tasks,
    set_completed_tasks,
    set_completed_user_stories,
    set_completed_features,
    set_completed_epics,
    set_met_acs,
    set_met_scs,
    set_status,
    set_all_status_in_progress,
    set_all_status_completed,
    reset_all_tasks_status,
    reset_all_acs_status,
    reset_all_scs_status,
    reset_all_user_story_status,
)

# Resolvers
from .resolvers import (
    initialize_tasks,
    initialize_acs,
    initialize_scs,
    refresh_current_tasks,
    record_completed_task,
    record_completed_user_story,
    record_completed_feature,
    record_completed_epic,
    record_met_ac,
    record_met_sc,
    resolve_tasks,
    resolve_completed_acs,
    resolve_completed_scs,
    resolve_user_story,
    resolve_feature,
    resolve_epic,
    resolve_state,
    increment_id,
)

__all__ = [
    # State
    "load_project_state",
    "save_project_state",
    "initialize_project_state",
    # Getters
    "get_project_name",
    "get_target_release",
    "get_current_version",
    "get_current_epic_id",
    "get_current_feature_id",
    "get_current_user_story",
    "get_current_tasks",
    "get_current_tasks_ids",
    "get_current_task_dependencies",
    "get_current_acs",
    "get_current_acs_ids",
    "get_current_scs",
    "get_current_scs_ids",
    "get_current_allowed_tasks",
    "get_completed_tasks",
    "get_completed_user_stories",
    "get_completed_features",
    "get_completed_epics",
    "get_met_acs",
    "get_met_scs",
    "get_tasks_with_completed_deps",
    # Checkers
    "is_task_completed",
    "is_ac_met",
    "is_sc_met",
    "is_user_story_completed",
    "is_feature_completed",
    "is_epic_completed",
    "are_task_deps_completed",
    "is_task_allowed",
    "find_tasks_allowed_in_user_story",
    # Setters
    "set_project_name",
    "set_target_release",
    "set_current_version",
    "set_current_epic_id",
    "set_current_feature_id",
    "set_current_user_story",
    "set_current_user_story_status",
    "set_current_tasks",
    "set_current_acs",
    "set_current_scs",
    "set_current_allowed_tasks",
    "set_completed_tasks",
    "set_completed_user_stories",
    "set_completed_features",
    "set_completed_epics",
    "set_met_acs",
    "set_met_scs",
    "set_status",
    "set_all_status_in_progress",
    "set_all_status_completed",
    "reset_all_tasks_status",
    "reset_all_acs_status",
    "reset_all_scs_status",
    "reset_all_user_story_status",
    # Resolvers
    "initialize_tasks",
    "initialize_acs",
    "initialize_scs",
    "refresh_current_tasks",
    "record_completed_task",
    "record_completed_user_story",
    "record_completed_feature",
    "record_completed_epic",
    "record_met_ac",
    "record_met_sc",
    "resolve_tasks",
    "resolve_completed_acs",
    "resolve_completed_scs",
    "resolve_user_story",
    "resolve_feature",
    "resolve_epic",
    "resolve_state",
    "increment_id",
]
