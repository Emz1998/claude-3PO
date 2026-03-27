# Coding Standards

> **Project:** `[Project Name]`
> **Last Updated:** `[Date]`
> **Version:** 1.0

---

## General Principles

- Favour clarity over cleverness.
- Follow the principle of least surprise.
- Leave the codebase better than you found it.
- Every standard in this document must be objectively verifiable — if an agent or linter can't check it, it doesn't belong here.

---

## Language & Type Safety

- **Language:** `[e.g. TypeScript, Python, Go]`
- **Strict mode:** `[e.g. TypeScript strict: true, Python mypy --strict]`
- `[Language-specific rules, e.g.:]`
  - `[No 'any' types unless absolutely necessary and commented why]`
  - `[Explicit return types on all exported/public functions]`
  - `[Type hints on all public function signatures]`

---

## Naming Conventions

| Element       | Style         | Example             |
| ------------- | ------------- | ------------------- |
| Variables     | `camelCase`   | `userCount`         |
| Constants     | `UPPER_SNAKE` | `MAX_RETRIES`       |
| Functions     | `camelCase`   | `fetchUserData()`   |
| Classes/Types | `PascalCase`  | `UserRepository`    |
| Components    | `PascalCase`  | `NoteEditor.tsx`    |
| Hooks         | `camelCase`   | `useNoteActions.ts` |
| Files         | `kebab-case`  | `user-service.ts`   |
| DB Tables     | `snake_case`  | `user_accounts`     |

Use descriptive, intention-revealing names. Avoid abbreviations unless universally understood (`id`, `url`, `http`).

> Adapt this table to your stack. Remove rows that don't apply (e.g. Hooks if not using React, DB Tables if no database).

---

## Formatting

Formatting is enforced by tooling, not humans or agents.

- **Formatter:** `[e.g. Prettier, Black, gofmt]`
- **Config file:** `[e.g. .prettierrc, pyproject.toml]`
- **Enforced via:** `[e.g. pre-commit hook, CI check]`

Key settings (for reference — the config file is the source of truth):

- Indentation: `[2 spaces / 4 spaces / tabs]`
- Max line length: `[80 / 100 / 120]`
- Quotes: `[single / double]`
- Semicolons: `[required / omitted]`
- Trailing commas: `[yes / no]`

> The Code Reviewer agent does NOT check formatting. The formatter handles it.

---

## Code Structure

- One component/class/module per file.
- Keep functions short — ideally under 30 lines.
- Limit function parameters to 3-4; use an options object beyond that.
- Avoid deep nesting — return early instead.
- Co-locate tests with source: `MyModule.test.ts` next to `MyModule.ts`
- `[Framework-specific patterns, e.g.:]`
  - `[Functional components only — no class components]`
  - `[Named exports — avoid default exports except for pages/routes]`

### Directory Structure

```
[Paste or describe your directory structure here]

Example:
src/
├── components/       # UI components
├── services/         # Business logic + API calls
├── hooks/            # Custom hooks
├── types/            # Shared type definitions
├── utils/            # Helper functions
└── config/           # App configuration
```

> The Code Reviewer agent checks that new files land in the correct directory per this structure.

---

## Comments & Documentation

- Don't comment _what_ the code does — make the code self-explanatory.
- Comment _why_ a non-obvious decision was made.
- Use doc comments for public APIs (`/** ... */`, docstrings, etc.).
- Remove commented-out code before merging.
- Reference `decisions.md` in comments when implementing a non-obvious architectural choice.

---

## Error Handling

- Never silently swallow errors — at minimum log with context.
- Use typed/custom errors where the language supports it.
- Fail fast: validate inputs at boundaries.
- Log errors with sufficient context (who, what, where).
- `[External service rules, e.g.:]`
  - `[All API/database calls: wrap in try/catch with fallback behavior]`
  - `[User-facing errors: display in UI, not just console]`
  - `[Network errors: handle timeout, auth failure, permission denied]`

---

## Testing Policy

### What Requires Tests

- `[e.g. Services, hooks, utility functions — anything with logic]`
- `[e.g. Components with conditional rendering or state management]`
- Bug fixes require a regression test.

### What Does NOT Require Tests

- `[e.g. Simple wrapper/display components with no logic]`
- `[e.g. Config files, type definitions, constants]`

### Test Standards

- **Framework:** `[e.g. Vitest, Jest, pytest]`
- **Naming:** `describe('functionName')` → `it('should [expected behaviour] when [condition]')`
- Keep tests independent — no shared mutable state.
- Prefer integration tests for critical paths, unit tests for logic.
- **Coverage target:** `[X% or "cover critical paths, not everything"]`

### Check Command

```bash
# Add to package.json scripts (or equivalent)
"check": "[e.g. tsc --noEmit && eslint src/ && vitest run]"
```

> `[check command]` must pass before any task enters QA review.

---

## AI-Specific Standards

> Remove this section if your project has no AI/LLM integration.

### Prompt Management

- All prompts live in `[designated directory, e.g. src/services/ai/prompts/]` as named template strings.
- Never hardcode prompts inline in components or service functions.
- Prompts must be version-trackable — no dynamic prompt generation from user input without sanitization.

### Response Handling

- All AI responses must be validated/parsed before use — never trust raw output.
- Define expected response schemas and validate against them.
- Handle malformed responses gracefully with fallback behavior.

### Performance & Cost

- Include timeout handling (`[X seconds]` default) for all AI calls.
- `[Optional: Log token usage per call for cost tracking]`
- `[Optional: Implement debouncing/throttling for real-time AI features]`

---

## Version Control

### Branch Naming

`[type]/[short-description]`

Examples: `feat/user-auth`, `fix/null-crash`, `chore/update-deps`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short description (TASK-XXX)
```

Examples:

- `feat(editor): implement term highlighting (TASK-003)`
- `fix(auth): handle expired token refresh (TASK-007)`
- `chore(deps): update vitest to v2.1`

Keep commits atomic — one logical change per commit.
Include task ID from sprint.md so commits trace back to sprint tasks.

---

## Dependencies

- Justify new dependencies — prefer standard library when feasible.
- Pin versions or use lock files.
- Audit dependencies for known vulnerabilities before adding.
- Document significant dependencies in architecture.md.

---

## Security

- Never commit secrets, tokens, or credentials — use environment variables or a secrets manager.
- Sanitize all user input.
- Follow the principle of least privilege.
- Keep dependencies patched and up to date.
- `[Project-specific security rules, e.g.:]`
  - `[API keys loaded from environment, never bundled in client code]`
  - `[Auth tokens stored securely, not in localStorage]`

---

## Agent Review Pipeline

> This section replaces traditional "Code Reviews" for our AI Scrum workflow.

Code quality is verified by two agents in sequence:

**1. QA Agent** — checks acceptance criteria (does it work?)
**2. Code Reviewer** — checks this document (is it clean?)

### What the Code Reviewer Checks Against This Document

- [ ] Language & type safety rules
- [ ] Naming conventions
- [ ] Code structure and file placement
- [ ] Error handling on external calls
- [ ] Test coverage per testing policy
- [ ] AI-specific standards (if applicable)
- [ ] Commit message format

### What the Code Reviewer Does NOT Check

- Formatting (the formatter handles this)
- Whether the feature works (QA Agent handles this)
- Architectural decisions (Scrum Master handles this at sprint close)

---

## Tooling Checklist

| Tool           | Choice                     |
| -------------- | -------------------------- |
| Formatter      | `[e.g. Prettier]`          |
| Linter         | `[e.g. ESLint]`            |
| Type Checker   | `[e.g. TypeScript strict]` |
| Test Framework | `[e.g. Vitest]`            |
| Check Command  | `[e.g. npm run check]`     |

---

_This document is updated during sprint retrospectives when new patterns are established. Changes are logged in retro.md._
