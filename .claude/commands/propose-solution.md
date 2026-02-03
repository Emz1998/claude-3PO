---
name: simplify-code
description: Analyze overengineered code, design, and architecture then simplify where applicable
allowed-tools: Read, Glob, Grep, Edit, Write, Task
argument-hint: <file-or-directory-path>
model: opus
---

**Goal**: Analyze target code for overengineering patterns and simplify while preserving functionality

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

### Phase 3: Simplification Plan

- For each finding, propose a concrete simplification with before/after comparison
- Rank findings by impact (high: reduces files/modules, medium: reduces indirection, low: cosmetic)
- Verify each simplification preserves existing behavior and public API surface
- Present findings to user as a structured report before making changes

### Phase 4: Apply Changes

- Only apply changes after user confirms the simplification plan
- Inline single-use abstractions directly at call sites
- Remove unused wrapper layers and pass-through functions
- Collapse unnecessary class hierarchies into plain functions or simple objects
- Replace over-configured patterns with direct implementations
- Delete dead code entirely (no commenting out, no `_unused` prefixes)

## Rules

- **NEVER** change external API contracts or public interfaces without explicit approval
- **NEVER** remove error handling at system boundaries (user input, network, file I/O)
- **NEVER** simplify security-related code (auth, validation, sanitization)
- **NEVER** apply changes without presenting the plan to the user first
- **DO NOT** add new abstractions while simplifying existing ones
- **DO NOT** refactor tests unless they test removed abstractions
- **DO NOT** conflate simplification with feature changes; keep scope to reducing complexity only

## Acceptance Criteria

- All identified overengineering patterns are documented with clear justification
- Proposed simplifications preserve existing functionality and public API
- Changes are only applied after user approval
- No regressions introduced (existing tests still pass)
- Net reduction in lines of code, files, or abstraction layers
- Report delivered summarizing what was simplified and why
