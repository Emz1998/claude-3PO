---
name: claude-hooks
description: Use PROACTIVELY when you need to create, update, configure, or validate Claude hooks for various events and integrations
argument-hint: <task-to-be-performed> <instructions>
---

**Goal**: Create, update or troubleshoot Claude Code hook scripts

**IMPORTANT**: Infer the task to be performed based on the user's request. If not clear, ask the user for more details.

## Instructions

**IMPORTANT**: For all tasks, you must always read the `.claude/skills/claude-hooks/references/hooks.md` file and `.claude/skills/claude-hooks/references/input-patterns.md` file to understand the hooks configuration and structure.

### If the task is to create a new hook

- Choose the appropriate hook schema sample to read from `.claude/skills/claude-hooks/input-schemas/` based on the task
- Explore the hooks directory in `.claude/hooks/` to understand the structure and identify useful patterns
- Create a plan first for hook creation and present it to the user. Do not write the plan in a file. Just present it in the conversation.
- Once the user approved, implement the plan
- Run `/simplify` skill to clean up the code
- Review the code, fix any issues if any
- Update the hooks registry file with the new hooks structure in `.claude/settings.local.json` file
- Test the hook using `echo` to pipe JSON input
- Provide report to main agent

### If the task is to refactor hooks

- Analyze the user revision request. If revision request is vague, ask the user for more details.
- Invoke `EnterPlanMode` tool to enter plan mode.
- Identify all the files that are needed to be revised. If not provided, ask the user for the file path.
- Choose the appropriate hook schema sample to read from `.claude/skills/claude-hooks/input-schemas/` based on the task
- Explore the hooks directory in `.claude/hooks/` to understand the structure and identify useful patterns
- Create a plan first for refactoring and present it to the user.
- Once the user approved, implement the refactoring plan.
- Run `/simplify` skill to clean up the code
- Review the code, fix any issues if any
- Update the hooks registry file with the new hooks structure in `.claude/settings.local.json` file
- Test the hook using `echo` to pipe JSON input
- Provide report to main agent

### If the task is to troubleshoot hooks

- Identify the file that is causing the issue based on the user inputs/arguments. If not provided, ask the user for the file path.
- Run tests to reproduce the issue
- Look at the registry file in `.claude/settings.local.json` to ensure the hook is registered and configured correctly
- Reread the hook documentation in `.claude/skills/claude-hooks/references/hooks.md` to check if the hook implementation is not outdated.
- Recheck json payload in the hook reference to see if there are any changes in the payload.
- Review the code to see if there are any issues.
- If issues are found, provide a plan to fix the issue to the user.
- Once approved, implement the fix
- Test the fix using `echo` to pipe JSON input
- Provide report to main agent

## Workflow

1. Read `.claude/skills/claude-hooks/references/hooks.md` for claude code hooks configuration
2. Determine the task to be performed: create, refactor, or troubleshoot hooks
3. Implement the task based on the instructions above
4. Validate the hook script against the acceptance criteria
5. Test the hook using `echo` to pipe JSON input
6. Provide report to main agent

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
          command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/my_hook.py'"
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
      command: "python3 '$CLAUDE_PROJECT_DIR/.claude/hooks/workflow/my_hook.py'"
---
```

Key rules for frontmatter hooks:
- Each event (e.g. `Stop`) contains a list of hook groups, each with a nested `hooks:` array
- The `command` value must be wrapped in double quotes
- File paths inside the command must be wrapped in single quotes
- `$CLAUDE_PROJECT_DIR` variable is supported
- `timeout` field is supported
- For subagents, `Stop` hooks are automatically converted to `SubagentStop`

## Constraints

- **NEVER** hardcode credentials or modify critical system files
- **NEVER** write hooks that can cause infinite loops
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
