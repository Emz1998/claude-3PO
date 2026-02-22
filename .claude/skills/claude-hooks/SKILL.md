---
name: claude-hooks
description: Use PROACTIVELY when you need to create, update, configure, or validate Claude hooks for various events and integrations
argument-hint: <task-to-be-performed> <instructions>
---

**Goal**: Create, update or troubleshoot Claude Code hook scripts

## Context

- **Task to be performed (create, refactor, troubleshoot)**: $0
- **Instructions**: $1

## Instructions

- If `Task to be performed` is `create`, then your main task is to create a new hook. Create a new hook in the `.claude/hooks/` directory based on `Instructions` provided by the user.
- If `Task to be performed` is `refactor`, then your main task is to refactor an existing hook. Refactor the hook in the `.claude/hooks/` directory based on `Instructions` provided by the user.
- If `Task to be performed` is `troubleshoot`, then your main task is to troubleshoot an existing hook. Troubleshoot the specified hook based on `Instructions` provided by the user.

## Workflow

1. Read `.claude/skills/hooks-management/references/hooks.md` for claude code hooks configuration
2. Read `.claude/skills/hooks-management/references/input-patterns.md` for claude code hook input patterns
3. Determine the task to be performed: create, revise, activate, deactivate or troubleshoot hooks
4. Implement the task based on the conditions below

## Conditions

### If the task is to create a new hook

- Choose the appropriate hook schema sample to read from `.claude/skills/hooks-management/input-schemas/` based on the task
- Explore the hooks directory in `.claude/hooks/` to understand the structure and identify useful patterns
- Create a plan first for hook creation and present it to the user. Do not write the plan in a file. Just present it in the conversation.
- Once the user approved, create a new hook in the `.claude/hooks/` directory with the structure provided in `.claude/skills/hooks-management/references/hooks-registry.json`
- Assess complexity of the hook script implementation. Revise if necessary.
- Update the hooks registry file with the new hooks structure
- Test the hook using `echo` to pipe JSON input
- Run `/command-management` skill to create a dry-run in `.claude/commands/dry-runs/{dry-run name}.md` for dry-run testing of the hook
- Provide report to main agent

**Important:** `Dry-run` is different from `echo` testing. `Dry-run` will fully invoke the hook script either with tools, prompts, or other events. While `echo` testing will only test the hook script with a JSON input to ensure no errors are present in the hook script.

### If the task is to activate/deactivate hooks

**If the task is to activate hooks**

- Activate hooks in the `.claude/settings.local.json` file with the structure provided in `.claude/skills/hooks-management/references/hooks-registry.json`
- Update the hooks registry file(`hooks-registry.json`) with the new hooks structure
- Provide report to main agent

**If the task is to deactivate hooks**

- Deactivate hooks in the `.claude/settings.local.json` by replacing the values of each section in the `hooks` section with an empty array

```json
{
  "hooks": {
    "PreToolUse": [],
    "PostToolUse": [],
    "PermissionRequest": [],
    "SessionStart": [],
    "SessionEnd": [],
    "UserPromptSubmit": [],
    "Stop": [],
    "SubagentStop": [],
    "PreCompact": [],
    "Notification": []
  }
}
```

- Provide report to main agent

### If the task is to revise hooks

- Analyze the user revision request. If revision request is vague, ask the user for more details.
- Identify the file that is needed to be revised. If not provided, ask the user for the file path.
- Choose the appropriate hook schema sample to read from `.claude/skills/hooks-management/input-schemas/` based on the task
- Explore the hooks directory in `.claude/hooks/` to understand the structure and identify useful patterns
- Create a plan first for hook revision and present it to the user. Do not write the plan in a file. Just present it in the conversation.
- Once the user approved, revise the hook script in the `.claude/hooks/` directory with the structure provided in `.claude/skills/hooks-management/references/hooks-registry.json`
- Revise the hook script in the `.claude/hooks/` directory with the structure provided in `.claude/skills/hooks-management/references/hooks-registry.json`
- Assess complexity of the hook script implementation. Revise if necessary.
- If a new hook is added/removed/updated, update the hooks registry file(`hooks-registry.json`) with the new hooks structure
- Test the hook using `echo` to pipe JSON input
- Provide report to main agent

### If the task is to troubleshoot hooks

- Identify the file that is causing the issue based on the user inputs/arguments. If not provided, ask the user for the file path.
- Diagnose the issue in that file
- Provide a plan to fix the issue to the user
- Once approved, implement the fix
- Test the fix using `echo` to pipe JSON input
- Provide report to main agent

## Constraints

- **NEVER** hardcode credentials or modify critical system files
- **NEVER** write hooks that can cause infinite loops
- **NEVER** bypass security validations
- **DO NOT** use multiline comments. Only single line comments (`#`).

## Acceptance Criteria

- Hook executes successfully on target event
- Hook handles invalid/malformed input gracefully
- Hook implementation is simple and not complex
- No security vulnerabilities
- Uses shared utilities from `.claude/hooks/utils/`
