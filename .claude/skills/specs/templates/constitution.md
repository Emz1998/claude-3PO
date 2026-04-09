# Project Constitution

> **Project:** `[Project Name]`
> **Version:** 1.0
> **Last Updated:** `[YYYY-MM-DD]`
> **Maintained by:** `[Role / Name]`

---

## How to Use This Document

This is the single source of truth for how this project is built, reviewed, and shipped. Every contributor — human or AI agent — is bound by it.

- **Builders** reference it while writing code.
- **Reviewers** check work against it.
- **Planners** use it to scope work realistically.

Update this document during retrospectives when new patterns are established. Log changes in `retro.md`.

---

# Governing Principles

> Define 4-8 principles that guide every decision in the project. When two goals conflict, contributors resolve by consulting this ordered list. Higher-numbered principles yield to lower-numbered ones.
>
> Each principle should be:
>
> - Actionable (tells someone what to do, not just what to value)
> - Specific enough to resolve a real disagreement
> - Ordered by priority relative to the others
>
> Examples of the kind of thing to write here:
>
> - "Ship working software over comprehensive documentation"
> - "Simplicity over cleverness — three clear lines beat one clever one"
> - "Automate anything a tool can check — manual enforcement is a process bug"
> - "Every commit traces to a task; every task traces to a goal"

1. **`[Principle Name]`** — `[One-sentence description of the principle and how to apply it]`
2. **`[Principle Name]`** — `[One-sentence description]`
3. **`[Principle Name]`** — `[One-sentence description]`
4. **`[Principle Name]`** — `[One-sentence description]`
5. **`[Principle Name]`** — `[One-sentence description]`
6. **`[Principle Name]`** — `[One-sentence description]`

---

# Development Guidelines

## Workflow

> Define the development cycle that all contributors follow. Describe each phase in one sentence.
> Consider phases like: Understand, Plan, Build, Verify, Report.

1. **`[Phase]`** — `[What happens in this phase]`
2. **`[Phase]`** — `[What happens in this phase]`
3. **`[Phase]`** — `[What happens in this phase]`
4. **`[Phase]`** — `[What happens in this phase]`
5. **`[Phase]`** — `[What happens in this phase]`

## Decision-Making

> Define how technical decisions are made and recorded.
> Consider: When to document in `decisions.md`, how to choose between equal approaches, when to escalate.

- `[Decision-making rule]`
- `[Decision-making rule]`
- `[Decision-making rule]`

## Dependencies

> Define rules for adding, managing, and auditing third-party dependencies.

- `[Dependency rule]`
- `[Dependency rule]`
- `[Dependency rule]`

## Version Control

### Branch Naming

> Define your branch naming convention.

`[pattern]` — e.g. `type/short-description`

### Commit Messages

> Define your commit message format. Reference a standard if applicable (e.g. Conventional Commits).

```
[format]
```

> Include rules about atomicity, task ID references, and scope.

- `[Commit rule]`
- `[Commit rule]`

## Security

> Define security rules that apply to all code in this project.
> Consider: secrets management, input sanitization, privilege model, dependency patching.

- `[Security rule]`
- `[Security rule]`
- `[Security rule]`
- `[Project-specific security rules:]`
  - `[e.g. API keys loaded from environment, never bundled in client code]`
  - `[e.g. Auth tokens stored securely, not in localStorage]`

---

# Coding Standards

## Language & Type Safety

> Define the primary language(s), strict mode settings, and language-specific rules.

- **Language:** `[e.g. TypeScript, Python, Go]`
- **Strict mode:** `[e.g. TypeScript strict: true, Python mypy --strict]`
- `[Language-specific rules:]`
  - `[e.g. No 'any' types unless commented why]`
  - `[e.g. Explicit return types on all exported functions]`
  - `[e.g. Type hints on all public function signatures]`

## Naming Conventions

> Define naming styles for each code element in your stack. Remove rows that don't apply, add rows for elements specific to your framework.

| Element     | Style     | Example     |
| ----------- | --------- | ----------- |
| `[Element]` | `[Style]` | `[Example]` |
| `[Element]` | `[Style]` | `[Example]` |
| `[Element]` | `[Style]` | `[Example]` |
| `[Element]` | `[Style]` | `[Example]` |
| `[Element]` | `[Style]` | `[Example]` |

> State any general naming rules (e.g. "avoid abbreviations unless universally understood").

## Formatting

> Formatting is enforced by tooling, not humans or agents. Define the tool and config — the config file is the source of truth.

- **Formatter:** `[e.g. Prettier, Black, gofmt]`
- **Config file:** `[e.g. .prettierrc, pyproject.toml]`
- **Enforced via:** `[e.g. pre-commit hook, CI check]`

Key settings (for reference only):

- Indentation: `[2 spaces / 4 spaces / tabs]`
- Max line length: `[80 / 100 / 120]`
- Quotes: `[single / double]`
- Semicolons: `[required / omitted]`
- Trailing commas: `[yes / no]`

## Code Structure

> Define rules for file organization, function size, nesting, and framework-specific patterns.

- `[Structure rule, e.g. one component/class/module per file]`
- `[Structure rule, e.g. functions under 30 lines]`
- `[Structure rule, e.g. max 3-4 function parameters]`
- `[Structure rule, e.g. return early to avoid deep nesting]`
- `[Structure rule, e.g. co-locate tests with source]`
- `[Framework-specific patterns:]`
  - `[e.g. Functional components only]`
  - `[e.g. Named exports preferred]`

### Directory Structure

> Paste or describe your directory layout. Reviewers check that new files land in the correct location.

```
[Your directory structure here]
```

## Comments & Documentation

> Define when comments are required, what kind, and what to avoid.

- `[Comment rule, e.g. comment why, not what]`
- `[Comment rule, e.g. doc comments for public APIs]`
- `[Comment rule, e.g. no commented-out code before merging]`
- `[Comment rule, e.g. reference decisions.md for non-obvious choices]`

## Error Handling

> Define how errors are handled, logged, and surfaced. Include rules for external service calls.

- `[Error handling rule, e.g. never silently swallow errors]`
- `[Error handling rule, e.g. use typed/custom errors]`
- `[Error handling rule, e.g. validate inputs at boundaries]`
- `[Error handling rule, e.g. log with context: who, what, where]`
- `[External service rules:]`
  - `[e.g. All API calls wrapped in try/catch with fallback]`
  - `[e.g. User-facing errors displayed in UI]`
  - `[e.g. Network errors: handle timeout, auth failure, permission denied]`

## AI-Specific Standards

> Remove this section if your project has no AI/LLM integration.
> Otherwise, define rules for prompt management, response handling, and cost control.

### Prompt Management

- `[e.g. All prompts live in a designated directory as named templates]`
- `[e.g. Never hardcode prompts inline]`
- `[e.g. No dynamic prompt generation from unsanitized user input]`

### Response Handling

- `[e.g. All AI responses validated/parsed before use]`
- `[e.g. Expected response schemas defined and enforced]`
- `[e.g. Malformed responses handled gracefully with fallback]`

### Performance & Cost

- `[e.g. Timeout handling on all AI calls]`
- `[e.g. Token usage logging for cost tracking]`
- `[e.g. Debouncing/throttling for real-time AI features]`

---

# Testing Policy

## Required Tests

> List the categories of code that must have tests.

- `[e.g. Services, hooks, utility functions — anything with logic]`
- `[e.g. Components with conditional rendering or state management]`
- `[e.g. Bug fixes require a regression test]`

## Exempt from Tests

> List what is explicitly exempt from test requirements.

- `[e.g. Simple wrapper/display components with no logic]`
- `[e.g. Config files, type definitions, constants]`

## Test Standards

> Define framework, naming conventions, isolation rules, and coverage targets.

- **Framework:** `[e.g. Vitest, Jest, pytest]`
- **Naming:** `[e.g. describe('functionName') -> it('should [behaviour] when [condition]')]`
- `[Test rule, e.g. keep tests independent — no shared mutable state]`
- `[Test rule, e.g. prefer integration tests for critical paths, unit tests for logic]`
- **Coverage target:** `[e.g. X% or "cover critical paths, not everything"]`
- **Check command:** `[e.g. npm run check]`

---

# Definition of Done

> Define checklists for each level. A task/sprint/release is Done when ALL items at its level pass.

## Task Done

- [ ] `[Automated gate item, e.g. check command passes with zero errors]`
- [ ] `[QA item, e.g. acceptance criteria verified]`
- [ ] `[QA item, e.g. critical logic paths covered by tests]`
- [ ] `[Review item, e.g. code follows this constitution's standards]`
- [ ] `[Review item, e.g. error handling on external calls]`
- [ ] `[Final item, e.g. committed with conventional message]`
- [ ] `[Final item, e.g. task status updated]`

## Story Done

> A story is done when all its tasks pass Task Done and the story-level criteria below are met.

- [ ] All tasks under this story meet Task Done
- [ ] Acceptance criteria from the story are verified end-to-end
- [ ] No regressions introduced to existing functionality
- [ ] Code reviewed against this constitution's coding standards
- [ ] Story status updated in sprint backlog

## Sprint Done

- [ ] `[e.g. All completed stories meet story-level DoD]`
- [ ] `[e.g. Features work together without conflicts]`
- [ ] `[e.g. Codebase matches architecture.md]`
- [ ] `[e.g. Smoke test: sprint goal works end-to-end]`
- [ ] `[e.g. Living docs updated (architecture.md, decisions.md, constitution.md)]`

## Out of Scope

> List items explicitly NOT required for the current milestone to prevent scope creep.

- `[e.g. Performance benchmarking]`
- `[e.g. Security audit]`
- `[e.g. Cross-platform testing]`
- `[e.g. CI/CD pipeline]`

---

# Tooling

> List the tools that enforce this constitution.

| Tool           | Choice                 |
| -------------- | ---------------------- |
| Formatter      | `[e.g. Prettier]`      |
| Linter         | `[e.g. ESLint]`        |
| Type Checker   | `[e.g. tsc --strict]`  |
| Test Framework | `[e.g. Vitest]`        |
| Check Command  | `[e.g. npm run check]` |

---

# Appendix — Agent Reference

> Define how each agent in your workflow uses this document. Remove or add rows to match your agent setup.

| Agent          | Uses Constitution For                               |
| -------------- | --------------------------------------------------- |
| `[Agent role]` | `[What this agent checks against in this document]` |
| `[Agent role]` | `[What this agent checks against in this document]` |
| `[Agent role]` | `[What this agent checks against in this document]` |
| `[Agent role]` | `[What this agent checks against in this document]` |
| `[Agent role]` | `[What this agent checks against in this document]` |

---

_This document is the project's constitution. Amend it deliberately, not casually._
