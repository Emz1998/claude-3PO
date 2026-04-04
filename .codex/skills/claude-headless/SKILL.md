---
name: claude-headless
description: Use PROACTIVELY when you need to create, update, configure, or validate Claude hooks for various events and integrations
argument-hint: <task-to-be-performed> <instructions>
---

**Goal**: Create, update or troubleshoot Claude Code headless claude scripts
**Claude Code Headless Claude Documentation**: @.claude/skills/claude-headless/references/headless-claude.md
**Claude Code CLI Reference Documentation**: @.claude/skills/claude-headless/references/claude-cli.md

**IMPORTANT**: Infer the task to be performed based on the user's request. If not clear, ask the user for more details.

## Instructions

**IMPORTANT**: Please explore the input schemas in `.claude/skills/claude-headless/input-schemas/` to understand the headless claude configuration and structure.

### If the task is to create a new headless claude script

- Read @.claude/skills/claude-headless/references/configuring-permissions.md to understand the configuring permissions for headless claude scripts.
- Use permission rules in `--allowedTools` to allow the tools that are needed to create the script.
- Do TDD(Test Driven Development) approach to create the script.
- Enter plan mode if not already, explore and then create a plan for the script.
- Review the code, fix any issues if any
- Provide report to the user

### If the task is to refactor or review headless claude scripts

- Analyze the user revision request. If revision request is vague, ask the user for more details.
- Enter plan mode if not already, explore and then create a plan for the script.
- Find existing tests for the script
- Refactor or revise the script according to the plan
- Do a regression test to ensure the script works as expected.
- Provide report to the user

### If the task is to troubleshoot headless claude scripts

- Identify the file that is causing the issue based on the user inputs/arguments. If not provided, ask the user for the file path.
- Run tests to reproduce the issue
- Review the code to see if there are any issues.
- If issues are found, enter plan mode, explore and then create a plan to fix the issue.
- Once approved, implement the fix and do a regression test to ensure the script works as expected.
- Provide report to the user

## Workflow

1. Read `.claude/skills/claude-headless/references/headless-claude.md` for claude code headless claude configuration
2. Read `.claude/skills/claude-headless/references/claude-cli.md` for claude code cli reference
3. Read `.claude/skills/claude-headless/output-schemas/` to understand the headless claude output schemas.
4. Determine the task to be performed: create, refactor, or troubleshoot hooks
5. Implement the task based on the instructions above
6. Validate the hook script against the acceptance criteria
7. Provide report to main agent

## Constraints

- **NEVER** hardcode credentials or modify critical system files
- **NEVER** write hooks that can cause infinite loops
- **NEVER** bypass security validations
- Always write the code in python.
- Ask the user first before removing any headless claude scripts from the directory.

## Acceptance Criteria

- Code is written in python
- Solutions are appropriate for the complexity of the task
- Code is robust and resilient to errors
- No tests are failing
- Headless claude scripts handles invalid/malformed input gracefully
- Headless claude scripts implementation is simple and not complex
- No security vulnerabilities
- Headless claude scripts are created in the correct directory `.claude/skills/claude-headless/scripts/`

## References

- **Claude Code Headless Claude Documentation**: @.claude/skills/claude-headless/references/headless-claude.md
- **Claude Code CLI Reference Documentation**: @.claude/skills/claude-headless/references/claude-cli.md
- **Claude Code Headless Input Schemas**: @.claude/skills/claude-headless/input-schemas/
- **Claude Code Headless Output Schemas**: @.claude/skills/claude-headless/output-schemas/
- **Script** directory: @.claude/scripts/workflows/
