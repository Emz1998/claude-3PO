# Guardrails Hooks

PreToolUse/SubagentStop hook that controls subagent permissions and tool access.

**Constraint:** Only runs when `/build` skill is active (`build_skill_active: true` in cache).

## Subagent Configurations

- **code-reviewer** - Write, Edit guarded to `revisions/revisions_{date}_{session}.md`
- **codebase-explorer** - Write, Edit guarded to `codebase-status/codebase-status_{date}_{session}.md`
- **fullstack-developer** - Write, Edit blocked for .md except README.md
- **gemini-manager** - Write, Edit guarded to `decisions/`, only discuss:gemini skill
- **gpt-manager** - Write, Edit guarded to `decisions/`, only discuss:gpt skill
- **plan-consultant** - Write, Edit guarded to `decisions/`
- **planner** - Write, Edit guarded to `plans/plan_{date}_{session}.md`
- **project-manager** - Write, Edit blocked, only log:ac, log:sc, log:task skills
- **test-engineer** - Write, Edit guarded to test files only (*.test.ts, __tests__/)
- **version-manager** - Write, Edit, MultiEdit blocked, safe git commands only

## Config Options

- `blocked` - Completely blocked tools
- `guarded` - Tools requiring path validation
- `validator` - Function to validate file paths
- `skills_allowed` - Whitelist of allowed skills
- `safe_bash_only` - Block non-safe git commands

## Usage

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
