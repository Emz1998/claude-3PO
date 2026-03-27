---
name: claude-command
description: Use PROACTIVELY this skill when you need to create or update custom commands following best practices
allowed-tools: Read, Write, SlashCommand, TodoWrite, Glob, Grep
argument-hint: <action-to-be-performed> <command-name> <instructions>
---

**Goal**: Create or update custom commands following template standards

**IMPORTANT**: Keep command content high-level and concise. Do not dive into implementation details.

## Context

- $0 = <action-to-be-performed>
- $1 = <command-name> or <instructions>
- $2 = <instructions> (conditionally required)

## Instructions

### If `Action to be performed` is `create`

> If `command-name` or `instructions` are not provided, then you should exit and ask the user to provide a command name and instructions.

- Create a new command in the `.claude/commands/` directory with the name of the `command-name`
- Configure the command with the `instructions` provided by the user.
- Validate the `command.md` file against the acceptance criteria and the template from `.claude/skills/claude-command/templates/command.md`.
- Save the `command.md` file to the `.claude/commands/command.md` file.

### If `Action to be performed` is `update`

> If `command-name` or `instructions` are not provided, then you should exit and ask the user to provide a command name and instructions.

- Update the existing command in the `.claude/commands/` directory with the name of the `command-name`
- Configure the command with the `instructions` provided by the user.
- Re-validate the `command.md` file against the acceptance criteria and the template from `.claude/skills/claude-command/templates/command.md`.

### If `Action to be performed` is `delete`

> If `command-name` is not provided, then you should exit and ask the user to provide a command name.

- Delete the existing command in the `.claude/commands/` directory with the name of the `command-name`
- Delete the `command.md` file from the `.claude/commands/command.md` file.

### If `Action to be performed` is `list`

- List all existing commands in the `.claude/commands/` directory.

> **Note**: Supporting files should be store within the command folder. E.g. `.claude/commands/`
> **Note**: The folder name and the command name should be the same.

## Workflow

1. Read the template from `.claude/skills/claude-command/templates/command.md`
2. Read skills-docs.md from `.claude/skills/claude-command/references/skills-docs.md`
3. Analyze user requirements and determine command location
4. Implement the task based on the instructions above.
5. Report completion with command details and location

## Rules

- DO NOT deviate from template structure (YAML frontmatter + all sections)
- NEVER save commands outside `.claude/commands/` directory
- DO NOT grant excessive tool permissions - apply least-privilege
- DO NOT skip validation step.

## Acceptance Criteria

- Command saved to correct location with complete YAML frontmatter
- All template sections populated
- Command saved to correct location with correct YAML frontmatter
- Report delivered with command details and location
