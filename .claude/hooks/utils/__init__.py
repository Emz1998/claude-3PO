from .input import read_stdin_json
from .output import log, success_response, block_response, add_context, success_output, print_and_exit, continue_response
from .cache import get_cache, set_cache, write_cache, load_cache
from .status import get_status, set_status
from .file_manager import read_file, write_file
from .json_handler import load_json, set_json, get_json
from .extractor import extract_slash_command_name
from .blockers import (
    is_code_file,
    is_safe_git_command,
    block_coding,
    block_commit,
    block_file_pattern,
    block_tool,
    block_unsafe_bash,
    create_phase_blocker,
    CODE_EXTENSIONS,
    SAFE_GIT_PATTERNS,
)
from .guardrail_base import (
    GuardrailConfig,
    GuardrailRunner,
    get_milestone_folder_name,
    get_milestone_context,
    create_directory_validator,
    create_session_file_validator,
    create_pattern_validator,
    create_extension_blocker,
)
from .roadmap import (
    # Type aliases
    StatusType,
    CriteriaStatusType,
    TestStrategyType,
    # Core utilities
    get_current_version,
    get_roadmap_path,
    load_roadmap,
    save_roadmap,
    get_project_dir,
    get_prd_path,
    load_prd,
    # Find utilities
    find_task_in_roadmap,
    find_ac_in_roadmap,
    find_sc_in_roadmap,
    find_milestone_in_roadmap,
    find_phase_in_roadmap,
    # Phase utilities
    is_checkpoint_phase,
    get_checkpoint_phases,
    all_milestones_completed,
    any_milestone_in_progress,
    # Milestone utilities
    get_milestone_mcp_servers,
    has_mcp_servers,
    get_incomplete_milestone_deps,
    all_tasks_completed,
    any_task_in_progress,
    all_scs_met,
    get_unmet_scs,
    # Task utilities
    get_task_test_strategy,
    is_tdd_task,
    is_ta_task,
    get_task_owner,
    is_parallel_task,
    get_incomplete_task_deps,
    all_acs_met,
    get_unmet_acs,
    # Criteria utilities
    get_ac_description,
    get_sc_description,
    get_ac_with_description,
    get_sc_with_description,
    # Query utilities
    get_tdd_tasks,
    get_ta_tasks,
    get_parallel_tasks,
    get_sequential_tasks,
    # Context utilities
    get_task_context,
    get_milestone_context as get_roadmap_milestone_context,
    get_phase_context,
    # Auto-resolver
    resolve_milestones_and_phases,
    update_current_pointer,
    update_summary,
    run_auto_resolver,
)

__all__ = [
    # Input/Output
    "read_stdin_json",
    "log",
    "success_response",
    "block_response",
    "add_context",
    "success_output",
    "print_and_exit",
    "continue_response",
    # Cache
    "get_cache",
    "set_cache",
    "write_cache",
    "load_cache",
    # Status
    "get_status",
    "set_status",
    # File manager
    "read_file",
    "write_file",
    # JSON handler
    "load_json",
    "set_json",
    "get_json",
    # Extractor
    "extract_slash_command_name",
    # Blockers
    "is_code_file",
    "is_safe_git_command",
    "block_coding",
    "block_commit",
    "block_file_pattern",
    "block_tool",
    "block_unsafe_bash",
    "create_phase_blocker",
    "CODE_EXTENSIONS",
    "SAFE_GIT_PATTERNS",
    # Guardrail base
    "GuardrailConfig",
    "GuardrailRunner",
    "get_milestone_folder_name",
    "get_milestone_context",
    "create_directory_validator",
    "create_session_file_validator",
    "create_pattern_validator",
    "create_extension_blocker",
    # Roadmap - Type aliases
    "StatusType",
    "CriteriaStatusType",
    "TestStrategyType",
    # Roadmap - Core utilities
    "get_current_version",
    "get_roadmap_path",
    "load_roadmap",
    "save_roadmap",
    "get_project_dir",
    "get_prd_path",
    "load_prd",
    # Roadmap - Find utilities
    "find_task_in_roadmap",
    "find_ac_in_roadmap",
    "find_sc_in_roadmap",
    "find_milestone_in_roadmap",
    "find_phase_in_roadmap",
    # Roadmap - Phase utilities
    "is_checkpoint_phase",
    "get_checkpoint_phases",
    "all_milestones_completed",
    "any_milestone_in_progress",
    # Roadmap - Milestone utilities
    "get_milestone_mcp_servers",
    "has_mcp_servers",
    "get_incomplete_milestone_deps",
    "all_tasks_completed",
    "any_task_in_progress",
    "all_scs_met",
    "get_unmet_scs",
    # Roadmap - Task utilities
    "get_task_test_strategy",
    "is_tdd_task",
    "is_ta_task",
    "get_task_owner",
    "is_parallel_task",
    "get_incomplete_task_deps",
    "all_acs_met",
    "get_unmet_acs",
    # Roadmap - Criteria utilities
    "get_ac_description",
    "get_sc_description",
    "get_ac_with_description",
    "get_sc_with_description",
    # Roadmap - Query utilities
    "get_tdd_tasks",
    "get_ta_tasks",
    "get_parallel_tasks",
    "get_sequential_tasks",
    # Roadmap - Context utilities
    "get_task_context",
    "get_roadmap_milestone_context",
    "get_phase_context",
    # Roadmap - Auto-resolver
    "resolve_milestones_and_phases",
    "update_current_pointer",
    "update_summary",
    "run_auto_resolver",
]
