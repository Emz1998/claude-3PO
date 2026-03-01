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
- Once the user approved, create a new hook in the `.claude/hooks/` directory with the structure provided in `.claude/skills/claude-hooks/references/hooks-registry.json`
- Assess complexity of the hook script implementation. Revise if necessary.
- Update the hooks registry file with the new hooks structure
- Test the hook using `echo` to pipe JSON input
- Update the `/home/emhar/avaris-ai/scripts/claude_hooks/test/dry_run_test.py` file with the new hook and run it to test the hook
- Provide report to main agent

### If the task is to refactor hooks

- Analyze the user revision request. If revision request is vague, ask the user for more details.
- Invoke `enter_plan_mode` tool to enter plan mode.
- Identify all the files that are needed to be revised. If not provided, ask the user for the file path.
- Choose the appropriate hook schema sample to read from `.claude/skills/claude-hooks/input-schemas/` based on the task
- Explore the hooks directory in `.claude/hooks/` to understand the structure and identify useful patterns
- Explore the hook scripts in `scripts/claude_hooks/` to understand the implementation and identify the code that is needed to be revised.
- Create a plan first for refactoring and present it to the user.
- Once the user approved, implement the refactoring plan and register the hooks in `.claude/settings.local.json` file

### If the task is to troubleshoot hooks

- Identify the file that is causing the issue based on the user inputs/arguments. If not provided, ask the user for the file path.
- Diagnose the issue in that file
- Provide a plan to fix the issue to the user
- Once approved, implement the fix
- Test the fix using `echo` to pipe JSON input
- Provide report to main agent

## Workflow

1. Read `.claude/skills/claude-hooks/references/hooks.md` for claude code hooks configuration
2. Read `.claude/skills/claude-hooks/references/input-patterns.md` for claude code hook input patterns
3. Determine the task to be performed: create, revise, activate, deactivate or troubleshoot hooks
4. Implement the task based on the conditions below
5. Assess the complexity of the hook script implementation if applicable. Revise if necessary.
6. Validate the hook script implementation.
7. Test the hook using `echo` to pipe JSON input
8. Provide report to main agent

## Constraints

- **NEVER** hardcode credentials or modify critical system files
- **NEVER** write hooks that can cause infinite loops
- **NEVER** bypass security validations
- Ask the user first before removing any hooks from the registry

## Acceptance Criteria

- Assess the complexity of the hook script implementation. Revise if necessary.
- Hook executes successfully on target event
- Hook handles invalid/malformed input gracefully
- Hook implementation is simple and not complex
- No security vulnerabilities
