---
name: c-review
description: test
---

## Instructions

- Review code against project coding standards — only check HOW it is written, not WHETHER it works
- Code to review: $ARGUMENTS (if no arguments, use `git diff` to identify recent changes)
- Read context files before reviewing: `project/docs/architecture/coding-standards.md`, `project/docs/architecture/architecture.md`, `project/docs/architecture/decisions.md`
- Evaluate code across 5 categories: Type Safety, Naming and Structure, Error Handling, Domain-Specific Standards, Test Quality
- Produce a structured pass/fail verdict with max 5 prioritized issues

## Workflow

### Phase 1: Gather Context

- Read `project/docs/architecture/coding-standards.md` for conventions to check against
- Read `project/docs/architecture/architecture.md` for expected file structure and patterns
- Read `project/docs/architecture/decisions.md` for settled technical choices to verify compliance
- Identify the code to review from $ARGUMENTS or `git diff`

### Phase 2: Review Against Categories

- **Type Safety and Language Standards**
  - TypeScript: strict mode compliance (no `any` without justification), explicit return types on exported functions, proper type definitions, interfaces/types for all data structures
  - Python: type hints on all public function signatures, no bare `except:`, dataclasses or Pydantic models for data structures
  - General: no hardcoded magic numbers/strings without named constants, no commented-out code, functions do one thing
- **Naming and Structure**
  - File/class/function naming follows coding-standards.md conventions
  - Files in correct directories per architecture.md
  - One component/class/module per file
  - Tests co-located or in designated test directory per standards
- **Error Handling**
  - External service calls wrapped with proper error handling
  - No silent error swallowing — at minimum log with context
  - User-facing errors handled gracefully (not raw stack traces)
  - Fail fast: inputs validated at boundaries
- **Domain-Specific Standards**
  - Web Frontend: components are presentational, no direct API/database calls from components, accessibility basics
  - AI/ML Integration: prompts stored in designated directory, AI/ML responses validated before use, timeout handling on external AI calls
- **Test Quality**
  - Tests exist for new logic
  - Tests are meaningful (not just "it runs without crashing")
  - Test names describe expected behavior: "should [outcome] when [condition]"
  - No shared mutable state between tests

### Phase 3: Compile Report

- Use the report template from [templates/report.md](templates/report.md)
- Use the issue template from [templates/issue.md](templates/issue.md) for each finding
- Score each category as PASS / FAIL / N/A with a one-line note if issue found
- Determine overall verdict: PASS or FAIL
- If FAIL, list max 5 issues prioritized by impact
- Add non-blocking warnings for things that could be better but are not violations

## Rules

- Max 5 issues — prioritize the most impactful
- Only fail on actual standard violations, not preferences
- Do not suggest refactors unless something violates coding-standards.md or decisions.md
- Do not re-evaluate whether the feature works — QA already verified that
- If everything follows standards, say PASS and stop
- Be specific — "Error handling could be better" is useless; "userService.py get_user() has no try/except around the database query" is useful

## Acceptance Criteria

- All 5 review categories evaluated with PASS / FAIL / N/A verdict
- Each finding includes specific file, function/line reference, and concrete fix action
- Overall verdict (PASS/FAIL) provided
- Findings reference rules from coding-standards.md, architecture.md, or decisions.md
- Report structured for immediate action by the builder
