---
name: assess-complexity
description: Assess the complexity of the codebase and identify overengineering patterns
allowed-tools: Read, Glob, Grep, Task
argument-hint: <file-or-directory-path>
model: opus
---

**Goal**: Assess the complexity of the codebase and produce a structured findings report. *Assessment only, no planning or code changes.*

## Workflow

### Phase 1: Analysis

- Read and understand the target files at `$ARGUMENTS`
- If a directory is provided, scan all source files recursively
- Identify the core purpose and business logic of each module
- Map dependencies and coupling between modules
- Catalog all abstractions, patterns, and architectural layers

### Phase 2: Detect Overengineering

- Flag unnecessary abstraction layers (wrappers that only delegate, single-implementation interfaces)
- Flag premature generalization (config-driven behavior with only one config, unused extension points)
- Flag over-abstracted patterns (factories that create one type, strategies with one strategy, builders for simple objects)
- Flag excessive indirection (more than 3 hops to reach actual logic)
- Flag dead code paths (unused exports, unreachable branches, feature flags that are always on/off)
- Flag redundant error handling (catching and rethrowing without transformation, try/catch around infallible code)
- Flag unnecessary type complexity (deeply nested generics, union types that are never narrowed)

### Phase 3: Report

- Produce a structured report with each finding containing: location, description, severity (high/medium/low), and justification
- Rank findings by severity (high: reduces files/modules, medium: reduces indirection, low: cosmetic)
- Include a summary section with total finding counts by severity
- Present the report to the user

## Constraints

- **NEVER** propose code changes, refactors, or simplification plans
- **NEVER** edit, write, or modify any files
- **NEVER** make assumptions about what should be simplified; only report what is observed
- **DO NOT** conflate assessment with action; this command is read-only analysis
- **DO NOT** assess security-related code (auth, validation, sanitization) as overengineered without strong evidence

## Acceptance Criteria

- All identified overengineering patterns are documented with location, description, severity, and justification
- Report includes a summary of total findings by severity
- No files were modified or created
- Report delivered to the user
