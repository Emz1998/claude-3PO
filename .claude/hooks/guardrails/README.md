# Guardrails Hooks

Consolidated PreToolUse hook that controls subagent permissions and tool access.

**Constraint:** Only runs when `/build` skill is active (`build_skill_active: true` in cache).

## Architecture

Single entry point `subagent_guardrail.py` handles all subagent guardrails using a registry pattern.

```python
# Registry of all guardrail configurations
GUARDRAIL_CONFIGS: dict[str, GuardrailConfig] = {
    "code-reviewer": GuardrailConfig(...),
    "codebase-explorer": GuardrailConfig(...),
    # ... more configs
}
```

## Subagent Configurations

| Subagent | Guarded Tools | Path/Skill Restrictions |
|----------|---------------|-------------------------|
| code-reviewer | Write, Edit | revisions/{date}_{session}.md |
| codebase-explorer | Write, Edit | codebase-status/{date}_{session}.md |
| fullstack-developer | Write, Edit | Blocks .md except README.md |
| gemini-manager | Write, Edit | decisions/, only discuss:gemini skill |
| gpt-manager | Write, Edit | decisions/, only discuss:gpt skill |
| plan-consultant | Write, Edit | decisions/ |
| planning-specialist | Write, Edit | plans/plan_{date}_{session}.md |
| project-manager | Blocks Write, Edit | only log:ac, log:sc, log:task skills |
| test-engineer | Write, Edit | test files only (*.test.ts, __tests__/) |
| version-manager | Blocks Write, Edit, MultiEdit | safe git commands only |

## Engineer Task Logger

Engineer agents (backend-engineer, frontend-engineer, fullstack-developer, html-prototyper, react-prototyper, test-engineer) have additional restrictions:

- **Block tools** until current task is `in_progress` in roadmap
- **Prevent stop** until current task is `completed` in roadmap
- Allows `/log:task` skill to update task status

## GuardrailConfig Options

- `target_subagent` - Subagent type to guard
- `cache_key` - Cache key for activation state
- `guarded_tools` - Tools requiring path validation
- `blocked_tools` - Completely blocked tools
- `allowed_skills` - Whitelist of allowed skills
- `blocked_skills_except` - Block all skills except listed
- `path_validator` - Function to validate file paths
- `block_unsafe_bash` - Block non-safe git commands

## Path Validators

- `create_directory_validator(subfolder)` - Allow writes to milestone subfolder
- `create_session_file_validator(subfolder, prefix)` - Session-specific files
- `create_pattern_validator(patterns, allow_match, error_msg)` - Regex-based
- `create_extension_blocker(ext, except_files)` - Block by extension

## Usage

Hook registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "command": "python3 .claude/hooks/guardrails/subagent_guardrail.py",
        "timeout": 5000
      }
    ],
    "SubagentStop": [
      {
        "command": "python3 .claude/hooks/guardrails/subagent_guardrail.py",
        "timeout": 5000
      }
    ]
  }
}
```
