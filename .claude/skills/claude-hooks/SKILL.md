---
name: claude-hooks
description: Use PROACTIVELY when you need to create, update, configure, or validate Claude hooks for various events and integrations
argument-hint: <task-to-be-performed> <instructions>
---

**Goal**: Create, update or troubleshoot Claude Code hook scripts
**Claude Code Hooks Documentation**: @.claude/skills/claude-hooks/references/hooks.md

**IMPORTANT**: Infer the task to be performed based on the user's request. If not clear, ask the user for more details.

## Instructions

- Make the script executable by running `chmod +x <script_name>.py`
- Use `$CLAUDE_PROJECT_DIR` variable to reference the project directory. Example: `"$CLAUDE_PROJECT_DIR"/.claude/hooks/tests/general_test.py`
- When testing the hook, use `echo` to pipe the hook input if applicable. Example: `echo '{"test": "test"}' | ".claude/hooks/tests/general_test.py"`
- Narrow down the hook with the appropriate matcher if applicable. Example: `matcher: "Skill|Task"`

## Workflow

1. Read `.claude/skills/claude-hooks/references/hooks.md` for claude code hooks configuration
2. Read the appropriate hook input schema in `.claude/skills/claude-hooks/input-schemas/` to understand the hooks configuration and structure.
3. Determine the task to be performed: create, refactor, or troubleshoot hooks
4. Implement the task based on user request
5. Validate the hook script against the acceptance criteria (See Acceptance Criteria section)
6. Test the hook using `echo` to pipe JSON input if applicable
7. Provide report to main agent

## Agent Frontmatter Hooks

When adding hooks to agent `.md` files (in `.claude/agents/`), use the nested `hooks:` array structure. This is **critical** — a flat structure will silently fail.

**Correct format:**

```yaml
---
name: my-agent
hooks:
  Stop:
    - hooks:
        - type: command
          command: "'$CLAUDE_PROJECT_DIR'/.claude/hooks/workflow/my_hook.py"
          timeout: 10
---
```

**Wrong format (hook will NOT fire):**

```yaml
---
name: my-agent
hooks:
  Stop:
    - type: command
      command: "'$CLAUDE_PROJECT_DIR'/.claude/hooks/workflow/my_hook.py"
---
```

## Constraints

- **NEVER** hardcode credentials or modify critical system files
- **NEVER** use absolute paths in the code. Use `$CLAUDE_PROJECT_DIR` variable to reference the project directory.
- **NEVER** bypass security validations
- Always write the code in python.
- Ask the user first before removing any hooks from the registry

## Acceptance Criteria

- Code is written in python
- Solutions are appropriate for the complexity of the task
- Code is robust and resilient to errors
- Hook executes successfully on target event
- Hook handles invalid/malformed input gracefully
- Hook implementation is simple and not complex
- No security vulnerabilities
- Agent frontmatter hooks use the correct nested `hooks:` array structure
