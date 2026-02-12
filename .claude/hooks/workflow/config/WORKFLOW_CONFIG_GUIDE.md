# Workflow Configuration Guide

This guide explains how to configure the workflow system using `workflow.config.yaml`. No programming or regex knowledge is required.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Project Settings](#project-settings)
3. [Workflow Phases](#workflow-phases)
4. [Bypass Phases](#bypass-phases)
5. [Triggers](#triggers)
6. [Agents](#agents)
7. [Deliverables](#deliverables)
8. [Feature Flags](#feature-flags)
9. [Environment Overrides](#environment-overrides)
10. [Pattern Syntax](#pattern-syntax)
11. [Common Scenarios](#common-scenarios)
12. [Troubleshooting](#troubleshooting)

---

## Quick Start

The workflow is configured in a single file: `workflow.config.yaml`

Here's the minimal configuration you need:

```yaml
project:
  name: "My Project"
  version: "v1.0.0"

phases:
  base:
    - explore
    - plan
    - code
    - commit

agents:
  explore: codebase-explorer
  plan: planner
  commit: version-manager
```

---

## Project Settings

Define basic information about your project:

```yaml
project:
  name: "My App - Description" # Your project name
  version: "v0.1.0" # Current version (e.g., v0.1.0, v1.2.3)
  target_release: "2025-03-15" # Target release date (optional)
```

These values are used in reports and state tracking.

---

## Workflow Phases

Phases define the order of work. The workflow moves through phases sequentially.

### Base Phases

The `base` phases are your main workflow:

```yaml
phases:
  base:
    - explore # Understand the codebase
    - plan # Create implementation plan
    - plan-consult # Review plan (optional)
    - finalize-plan # Finalize plan (optional)
    - code # Write code (expands to TDD or test-after)
    - commit # Commit changes
```

### The Special "code" Phase

The `code` phase is a placeholder that expands based on your testing strategy:

**TDD Strategy** (Test-Driven Development):

```yaml
phases:
  tdd:
    - write-test # Write failing tests first
    - review-test # Review test quality
    - write-code # Write code to pass tests
    - code-review # Review code quality
    - refactor # Clean up code
    - validate # Run all checks
```

**Test-After Strategy**:

```yaml
phases:
  test-after:
    - write-code # Write code first
    - write-test # Write tests after
    - review-test # Review tests
    - code-review # Review code
    - refactor # Clean up
    - validate # Final validation
```

### Simple Workflow

For smaller projects without TDD:

```yaml
phases:
  simple:
    - explore
    - plan
    - execute
    - commit
```

---

## Bypass Phases

Bypass phases allow jumping out of normal phase order for special operations like troubleshooting. They can only be entered from certain phases.

```yaml
bypass_phases:
  troubleshoot:
    can_bypass:      # Phases you CAN enter troubleshoot from
      - write-tests
      - review-tests
      - write-code
      - code-review
      - refactor
      - validate
      - commit
    cannot_bypass:   # Phases you CANNOT enter troubleshoot from
      - explore
      - plan
      - plan-consult
      - finalize-plan
```

**How it works:**

- Use `/troubleshoot` to enter troubleshoot mode from any coding phase
- Pre-coding phases (explore, plan, etc.) are protected and cannot be bypassed
- The previous phase is stored so you can return after troubleshooting
- Use `/troubleshoot` again to exit and return to the previous phase

**Use case:** When you encounter an unexpected issue during coding that requires investigation without losing your workflow position.

---

## Triggers

Triggers are the commands that activate, deactivate, or change the workflow mode. Each trigger has a `command` (the slash command) and optional validation fields.

```yaml
triggers:
  implement:
    command: "/implement"
    arg_pattern: "MS-\\d{3}$"  # Regex to validate the argument
    arg_hint: "MS-NNN"          # Shown in usage hints
    description: "Activate workflow and begin implementation"
  deactivate:
    command: "/deactivate-workflow"
    description: "Deactivate the workflow"
  dry_run:
    command: "/dry-run"
    description: "Activate dry-run mode"
  troubleshoot:
    command: "/troubleshoot"
    description: "Enter troubleshoot mode (bypasses coding phases)"
```

**Fields:**

- `command` - the slash command string (e.g. `/implement`)
- `arg_pattern` - *(optional)* regex pattern to validate the command argument
- `arg_hint` - *(optional)* human-readable hint for the expected argument format
- `description` - *(optional)* what the trigger does

**Important!** The `arg_pattern` value uses regex syntax (not wildcards). Backslashes must be doubled in YAML (`\\d` instead of `\d`).

If the `triggers` section is omitted, defaults are used: `/implement`, `/deactivate-workflow`, `/dry-run`, and `/troubleshoot`.

---

## Agents

Agents are the "workers" that handle each phase. Assign an agent to each phase:

```yaml
agents:
  explore: codebase-explorer # Analyzes codebase
  plan: planner # Creates plans
  plan-consult: plan-consultant # Reviews plans
  finalize-plan: planner # Finalizes plans
  commit: version-manager # Handles commits
  write-test: test-engineer # Writes tests
  review-test: test-reviewer # Reviews tests
  write-code: main-agent # Writes code
  code-review: code-reviewer # Reviews code
  refactor: main-agent # Refactors code
  validate: validator # Validates everything
  troubleshoot: troubleshooter # Diagnoses and resolves issues
```

### Available Agents

| Agent               | Purpose                                    |
| ------------------- | ------------------------------------------ |
| `codebase-explorer` | Analyzes codebase structure and patterns   |
| `planner`           | Creates and finalizes implementation plans |
| `plan-consultant`   | Reviews plans and provides feedback        |
| `main-agent`        | General-purpose coding agent               |
| `test-engineer`     | Writes unit and integration tests          |
| `test-reviewer`     | Reviews test quality and coverage          |
| `code-reviewer`     | Reviews code quality and best practices    |
| `validator`         | Runs validation checks and tests           |
| `version-manager`   | Handles git commits and versioning         |
| `troubleshooter`    | Diagnoses and resolves development issues  |

---

## Deliverables

Deliverables define what files each phase reads and produces.

### Basic Structure

```yaml
deliverables:
  phase-name:
    read: # Files to read (inputs)
      - ...
    write: # Files to create (outputs)
      - ...
    edit: # Existing files to modify
      - ...
    bash: # Commands to run
      - ...
    skill: # Skills to invoke
      - ...
```

### File Deliverables (read/write/edit)

Use the `filepath` field to specify file locations. It supports glob patterns, placeholders, and exact matching.

**Basic filepath:**

```yaml
read:
  - filepath: "prompt.md"
    description: "User's requirements"
```

**Pattern in subfolder:**

```yaml
write:
  - filepath: "reports/report_*.md"
    description: "Generated report"
```

**Recursive pattern:**

```yaml
edit:
  - filepath: "src/**/*.ts"
    description: "Any TypeScript file in src/"
```

### Placeholders

Dynamic path resolution using placeholders:

- `{project}` - Current feature path (e.g., `.claude/hooks/workflow/feature-name`)
- `{session}` - Current session ID (for session-scoped files)

```yaml
write:
  - filepath: "{project}/reports/report_{session}.md"
    description: "Session-scoped report in current feature folder"
```

### Exact Match (Repo Root)

Prefix with `./` to match files only at the repository root (not in subdirectories):

```yaml
read:
  - filepath: "./prompt.md"      # Only matches /repo/prompt.md
    description: "Root prompt file"
  - filepath: "prompt.md"        # Matches prompt.md anywhere
    description: "Any prompt file"
```

### Backward Compatibility

The legacy `folder`/`pattern`/`file` syntax still works:

```yaml
# Legacy syntax (still supported)
read:
  - file: "prompt.md"
  - folder: "reports"
    pattern: "*.md"

# New syntax (preferred)
read:
  - filepath: "prompt.md"
  - filepath: "reports/*.md"
```

### Command Deliverables (bash)

Run shell commands during a phase:

```yaml
bash:
  - command: "npm test"
    description: "Run test suite"
    allow_failure: false # Block if fails (default)

  - command: "npm run lint"
    description: "Check code style"
    allow_failure: true # Continue even if fails
```

### Skill Deliverables (invoke)

Invoke slash commands:

```yaml
skill:
  - name: "commit"
    description: "Invoke /commit skill"
```

### Strict Order

`strict_order` enforces execution order by actively blocking tool calls. When set, the PreToolUse handler blocks all tool calls that don't match the current minimum strict-order level:

- Optional integer field (lower = first)
- While any `strict_order` deliverables are incomplete, **only tools matching the current level are allowed**
- Once all `strict_order` deliverables are complete, all tools are unlocked
- Deliverables without `strict_order` are unaffected by this mechanism

```yaml
read:
  - file: "prompt.md"
    strict_order: 1  # Must be read before anything else
write:
  - folder: "reports"
    pattern: "report_*.md"
    strict_order: 2  # Only allowed after level 1 is complete
```

### Match Groups (OR Deliverables)

When a phase lists multiple file patterns for the same purpose (e.g., `.test.ts`, `.test.tsx`, `.py` test files) but the project only uses one language, use `match` to group them. Completing any one entry in a group satisfies the whole group.

- Entries sharing a `match` value within the same action are OR'd
- The name is arbitrary, used only for grouping
- Scoped per action — same name under `read:` and `write:` are independent groups
- Entries without `match` remain individually required (AND'd)

```yaml
edit:
  - folder: "src"
    pattern: "**/*.test.ts"
    description: "Test files"
    match: test-files
  - folder: "src"
    pattern: "**/*.test.tsx"
    description: "React test files"
    match: test-files
  - folder: "tests"
    pattern: "**/*.py"
    description: "Python test files"
    match: test-files
```

In this example, editing any one of `.test.ts`, `.test.tsx`, or `.py` files satisfies the `test-files` group.

---

## Feature Flags

Enable or disable workflow features:

```yaml
features:
  dry_run: false # true = simulate without changes
  strict_phase_order: true # true = enforce phase order
  require_deliverables: true # true = require deliverables
  verbose_logging: false # true = extra debug output
```

---

## Environment Overrides

Different settings for different environments:

```yaml
environments:
  dev:
    features:
      dry_run: true # Simulate in dev
      verbose_logging: true # Extra logging in dev

  prod:
    features:
      dry_run: false
      strict_phase_order: true
```

To use an environment, specify it when loading the config.

---

## Pattern Syntax

Use simple wildcards instead of complex regex:

| Pattern | Matches                | Example                                 |
| ------- | ---------------------- | --------------------------------------- |
| `*`     | Any characters (not /) | `*.md` matches `readme.md`              |
| `**`    | Any path including /   | `**/*.ts` matches `src/utils/helper.ts` |
| `?`     | Single character       | `file?.md` matches `file1.md`           |

### Examples

```yaml
# Match any markdown file
pattern: "*.md"

# Match any TypeScript file anywhere in src/
pattern: "**/*.ts"

# Match dated reports
pattern: "report_*.md"        # Matches report_20250101.md

# Match test files
pattern: "**/*.test.ts"       # Matches src/utils/helper.test.ts
```

---

## Common Scenarios

### Scenario 1: Simple Bug Fix Workflow

```yaml
phases:
  base:
    - explore
    - code
    - commit

agents:
  explore: codebase-explorer
  code: main-agent
  commit: version-manager
```

### Scenario 2: Full TDD Workflow

```yaml
phases:
  base:
    - explore
    - plan
    - plan-consult
    - finalize-plan
    - code
    - commit

  tdd:
    - write-test
    - review-test
    - write-code
    - code-review
    - refactor
    - validate
```

### Scenario 3: Documentation-Only Project

```yaml
phases:
  base:
    - explore
    - plan
    - execute
    - commit

deliverables:
  execute:
    edit:
      - folder: "docs"
        pattern: "**/*.md"
        description: "Documentation files"
```

### Scenario 4: Custom Validation Steps

```yaml
deliverables:
  validate:
    bash:
      - command: "npm test"
        description: "Unit tests"
      - command: "npm run e2e"
        description: "End-to-end tests"
      - command: "npm run lint"
        description: "Linting"
        allow_failure: true
      - command: "npm run typecheck"
        description: "Type checking"
```

### Scenario 5: Using Troubleshoot Mode

When you encounter an unexpected error during `write-code` phase:

1. Invoke `/troubleshoot` to enter troubleshoot mode
2. The `troubleshooter` agent investigates the issue
3. Once resolved, invoke `/troubleshoot` again to return to `write-code`

```yaml
# Configuration needed for troubleshoot
agents:
  troubleshoot: troubleshooter

bypass_phases:
  troubleshoot:
    can_bypass:
      - write-code
      - refactor
      - validate
    cannot_bypass:
      - explore
      - plan
```

---

## Troubleshooting

### Error: "Missing required section"

**Problem:** Configuration file is missing a required section.

**Solution:** Add the missing section. Required sections are:

- `project`
- `phases`
- `agents`

### Error: "No agent assigned for phase"

**Problem:** A phase is used but no agent is assigned.

**Solution:** Add the agent mapping:

```yaml
agents:
  missing-phase: agent-name
```

### Error: "Invalid YAML"

**Problem:** YAML syntax error.

**Solution:** Check for:

- Missing colons after keys
- Incorrect indentation (use 2 spaces)
- Missing quotes around special characters

### Deliverables Not Working

**Problem:** Files aren't being detected.

**Solution:** Check your `filepath` patterns:

1. Use `**` for recursive matching (e.g., `src/**/*.ts`)
2. Use `./` prefix for exact repo root matches
3. Ensure placeholders like `{project}` resolve correctly

**Example fix:**

```yaml
# Wrong - won't match files in subdirectories
filepath: "src/*.ts"

# Right - matches files in any subdirectory
filepath: "src/**/*.ts"
```

### Dry Run Mode

To test without making changes:

```yaml
features:
  dry_run: true
```

Or use the dev environment:

```yaml
environments:
  dev:
    features:
      dry_run: true
```

---

## Migration from JSON

If you're migrating from `workflow_config.json`:

1. The YAML format uses the same structure
2. Regex patterns are automatically converted from the JSON format
3. The JSON file will still work but shows a deprecation warning
4. Once migrated, you can delete the JSON file

### Pattern Changes

Old (JSON regex):

```json
"pattern": ".*codebase-status/codebase-status_.*\\.md$"
```

New (YAML filepath):

```yaml
filepath: "codebase-status/codebase-status_*.md"
```

---

## Getting Help

1. Check the error message - it tells you exactly what to fix
2. Review this guide for the correct syntax
3. Look at the default `workflow.config.yaml` for examples
4. Enable verbose logging for more details:
   ```yaml
   features:
     verbose_logging: true
   ```
