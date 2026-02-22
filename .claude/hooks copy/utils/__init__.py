from .output import (
    log,
    success_response,
    block_response,
    add_context,
    success_output,
    print_and_exit,
    continue_response,
)
from .cache import get_cache, set_cache, save_cache, load_cache, append_cache
from .state import StateManager
from .hook_manager import Hook
from .hook_state import HookState
from .decision import Output
from .parsers import extract_slash_command_name

from .files import (
    read_file,
    write_file,
    FileReadError,
)

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

__all__ = [
    # Input/Output
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
    "save_cache",
    "load_cache",
    "append_cache",
    # Files
    "read_file",
    "write_file",
    "extract_slash_command_name",
    "FileReadError",
    # JSON handler
    "StateManager",
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
    # Hook state
    "HookState",
    # Hook manager
    "Hook",
    # Decision
    "Output",
]
