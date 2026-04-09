---
name: claude-hooks
description: Use PROACTIVELY when you need to create, update, configure, or validate Claude hooks for various events and integrations
argument-hint: <task-to-be-performed> <instructions>
---

**Claude Hooks Documentation**: ${CLAUDE_SKILL_DIR}/references/hooks.md
!`./.claude/skills/claude-hooks/scripts/inject_context.py '$ARGUMENTS'`

## Anti-Patterns

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
