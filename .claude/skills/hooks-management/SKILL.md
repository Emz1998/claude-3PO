---
name: hooks-management
description: Use PROACTIVELY when you need to create, update, configure, or validate Claude hooks for various events and integrations
---

**Goal**: Create, update or troubleshoot Claude Code hook scripts

## Instructions

- **MUST** include proper error handling
- **MUST** prefer Python over shell scripts
- **MUST** use `sys.path.insert(0, str(Path(__file__).parent.parent))` to import utils
- **MUST** use type hints and type checking
- **MUST** use `# type: ignore` to suppress type errors

## Workflow

1. Read `.claude/skills/hooks-management/references/hooks.md` for claude code hooks configuration
2. Read `.claude/skills/hooks-management/references/input-patterns.md` for claude code hook input patterns
3. Choose the appropriate hook schema sample to read from `.claude/skills/hooks-management/input-schemas/` based on the task
4. Explore the hooks directory in `.claude/hooks/` to understand the structure and identify useful patterns

5. Create or update the hook script in `.claude/hooks/`
6. Assess complexity of the hook script implementation. Revise if necessary.
7. Verify hook execution using `echo` to pipe JSON input
8. Provide report to main agent

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
