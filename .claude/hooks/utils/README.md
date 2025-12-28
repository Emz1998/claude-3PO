# Hook Utilities

Shared utilities for all hook scripts.

## Input/Output

**input.py**
- `read_stdin_json()` - Parse JSON from stdin, returns dict or None

**output.py**
- `log(message)` - Write to log file
- `success_response()` - Exit 0 with success
- `block_response(reason)` - Exit 2 with block message
- `add_context(text)` - Add context to hook output
- `success_output()` - Return success JSON

## Cache and Status

**cache.py**
- `get_cache(key)` - Get value from cache
- `set_cache(key, value)` - Set cache value
- `load_cache()` - Load full cache dict
- `write_cache(cache)` - Write full cache dict

**status.py**
- `get_status(key)` - Get project status value
- `set_status(key, value)` - Set project status value

## File Operations

**file_manager.py**
- `read_file(path)` - Read file contents
- `write_file(path, content)` - Write file contents

**json_handler.py**
- `load_json(path)` - Load JSON file
- `set_json(path, key, value)` - Set JSON key
- `get_json(path, key)` - Get JSON key

## Blockers

**blockers.py**
- `is_code_file(path)` - Check if source code file
- `is_safe_git_command(cmd)` - Validate git command safety
- `block_coding(path, reason)` - Block code modifications
- `block_commit(cmd, reason)` - Block git commits
- `block_file_pattern(path, pattern, reason)` - Block by pattern
- `block_tool(tool_name, reason)` - Block specific tool
- `block_unsafe_bash(cmd)` - Block unsafe bash
- `create_phase_blocker(phases, action)` - Phase-specific blocker
- `CODE_EXTENSIONS` - Set of code file extensions
- `SAFE_GIT_PATTERNS` - Safe git command patterns

## Guardrail Base

**guardrail_base.py**
- `GuardrailConfig` - Configuration for guardrails
- `GuardrailRunner` - Execute guardrail logic
- `get_folder_name(id, name)` - Format folder name as ID_slug
- `get_phase_folder_name(roadmap, id)` - Format phase folder
- `get_milestone_folder_name(roadmap, id)` - Format milestone folder
- `get_milestone_context()` - Get version, phase, milestone, session
- `create_directory_validator(subfolder)` - Directory path validator
- `create_session_file_validator(subfolder, prefix)` - Session file validator
- `create_pattern_validator(patterns, allow, msg)` - Regex validator
- `create_extension_blocker(ext, except_files)` - Extension blocker

## Other Utilities

**extractor.py**
- `extract_slash_command_name()` - Extract command from input

**validation.py**
- Input validation helpers

**roadmap.py**
- `get_current_version()` - Get project version
- `get_roadmap_path(version)` - Get roadmap file path
- `load_roadmap(path)` - Load roadmap data
- `find_milestone_in_roadmap(roadmap, id)` - Find milestone

**checklist.py**
- Checklist management utilities

## Import Pattern

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json, block_response, get_cache
```
