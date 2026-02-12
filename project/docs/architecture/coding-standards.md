# Coding Standards

**Project:** Avaris
**Version:** v1.0
**Last Updated:** 2026-02-10

---

## General Principles

- Favour clarity over cleverness
- Follow the principle of least surprise
- Leave the codebase better than you found it
- Every standard here must be objectively verifiable by a linter or code reviewer

---

## Language and Type Safety

**TypeScript (Web Application)**

- Strict mode enabled (`strict: true` in tsconfig.json)
- No `any` types unless absolutely necessary and commented with why
- Explicit return types on all exported functions
- Use `unknown` instead of `any` when type is truly unknown
- Prefer `interface` for object shapes, `type` for unions and intersections

**Python (ML Pipeline)**

- Type hints on all public function signatures
- Use `mypy` for static type checking
- Target Python 3.11+ (match GitHub Actions runner)

---

## Naming Conventions

- **Variables** - `camelCase` - `userCount`, `winRate`
- **Constants** - `UPPER_SNAKE` - `MAX_RETRIES`, `MODEL_VERSION`
- **Functions** - `camelCase` (TS) / `snake_case` (Python) - `fetchGameData()` / `fetch_game_data()`
- **Classes/Types** - `PascalCase` - `GamePrediction`, `DashboardProps`
- **React Components** - `PascalCase` - `PredictionCard.tsx`, `DashboardChart.tsx`
- **Hooks** - `camelCase` with `use` prefix - `usePredictions.ts`
- **Files (TS)** - `kebab-case` - `game-prediction.ts`, `dashboard-service.ts`
- **Files (Python)** - `snake_case` - `feature_engineering.py`, `model_trainer.py`
- **Firestore collections** - `snake_case` - `predictions`, `blog_metadata`

Use descriptive, intention-revealing names. Avoid abbreviations unless universally understood (`id`, `url`, `api`).

---

## Formatting

Formatting is enforced by tooling, not humans.

**TypeScript/JavaScript**

- **Formatter** - Prettier
- **Config** - `.prettierrc`
- **Enforced via** - Pre-commit hook + CI check

**Key settings** (config file is source of truth):

- Indentation: 2 spaces
- Max line length: 100
- Quotes: single
- Semicolons: required
- Trailing commas: all

**Python**

- **Formatter** - Black
- **Config** - `pyproject.toml`
- **Line length** - 100

---

## Code Structure

- One component/class/module per file
- Keep functions under 30 lines; extract if longer
- Limit function parameters to 3-4; use an options object beyond that
- Avoid deep nesting; return early instead
- Functional components only; no class components
- Named exports only; avoid default exports except for Next.js pages

**Directory Structure**

```
/src
  /app            - Next.js App Router pages (thin wrappers)
  /components     - React UI components
  /lib            - Business logic, Firebase client, utilities
  /types          - Shared TypeScript type definitions
/pipeline
  /data           - Data ingestion and feature engineering
  /model          - XGBoost training and prediction
  /publish        - Content generation and Firestore writes
  /tests          - Python tests (pytest)
```

**Import rules:**

- `/app` routes can import from `/components`, `/lib`, `/types`
- `/components` can import from `/lib`, `/types`
- `/lib` must NOT import from `/app` or `/components`
- Python `/pipeline` modules must NOT import from `/src`

---

## Comments and Documentation

- Don't comment _what_ the code does; make the code self-explanatory
- Comment _why_ a non-obvious decision was made
- Use JSDoc (`/** ... */`) for exported functions in `/lib`
- Use Python docstrings for public functions in `/pipeline`
- Remove commented-out code before merging
- Reference `decisions.md` when implementing a non-obvious architectural choice

---

## Error Handling

- Never silently swallow errors; at minimum log with context
- Fail fast: validate inputs at boundaries
- Log errors with sufficient context (what operation, what data)

**TypeScript specific:**

- All Firebase/Firestore calls: wrap in try/catch with meaningful error messages
- Use typed error responses where applicable
- User-facing errors: display in UI, not just console

**Python specific:**

- All NBA API calls: wrap in try/except with retry logic
- All file I/O: wrap in try/except with cleanup
- Pipeline failures: log error and exit with non-zero code (triggers GitHub Actions alert)

---

## Testing Policy

**What Requires Tests**

- Services, hooks, utility functions (anything with logic)
- Data processing and feature engineering functions (Python)
- Model prediction output format and validation
- Components with conditional rendering or state

**What Does NOT Require Tests**

- Simple wrapper/display components with no logic
- Config files, type definitions, constants
- Next.js page files that only compose components

**Test Standards**

- **Web framework** - Vitest
- **Pipeline framework** - pytest
- **Naming** - `describe('functionName')` / `it('should [expected] when [condition]')`
- **Python naming** - `test_function_name_when_condition_then_expected`
- Keep tests independent; no shared mutable state
- Prefer integration tests for critical paths, unit tests for logic
- **Coverage target** - Cover critical paths, not everything

**Check Commands**

```bash
# TypeScript
npm run check    # tsc --noEmit && eslint src/ && vitest run

# Python
cd pipeline && python -m pytest && mypy .
```

_Check commands must pass before any task enters review._

---

## AI/ML-Specific Standards

**Model Management**

- Model artifacts stored in `/pipeline/model/artifacts/` (gitignored, rebuilt on each run)
- Model hyperparameters defined in `/pipeline/model/config.py` as named constants
- Feature lists maintained in `/pipeline/data/features.py`

**Data Pipeline**

- All data transformations must be deterministic given the same input
- Cache raw API responses to avoid redundant API calls during development
- Log data quality metrics (missing values, row counts) on each pipeline run

**Prediction Output**

- All predictions must include: game_id, date, home_team, away_team, predicted_winner, probability
- Probabilities must be between 0.0 and 1.0; validate before writing to Firestore
- Never publish predictions without validation against expected schema

---

## Version Control

**Branch Naming** - `[type]/[short-description]`

- Examples: `feat/prediction-dashboard`, `fix/firestore-query`, `chore/update-deps`

**Commit Messages** - Follow Conventional Commits:

- Format: `type(scope): short description`
- Examples:
  - `feat(dashboard): add win rate chart`
  - `fix(pipeline): handle postponed games`
  - `chore(deps): update next.js to 15.1`
- Keep commits atomic; one logical change per commit

---

## Dependencies

- Justify new dependencies; prefer standard library when feasible
- Pin versions using lock files (`package-lock.json`, `requirements.txt`)
- Audit dependencies for known vulnerabilities before adding
- Document significant dependencies in `architecture.md`

---

## Security

- Never commit secrets, tokens, or credentials; use environment variables
- Firebase service account key only in GitHub Secrets, never in repo
- API keys loaded from environment, never bundled in client code
- Sanitize any future user input (not applicable at MVP, but enforce from the start)
- Keep dependencies patched and up to date

---

## Tooling Checklist

- **Formatter (TS)** - Prettier
- **Formatter (Python)** - Black
- **Linter** - ESLint
- **Type Checker (TS)** - TypeScript strict mode
- **Type Checker (Python)** - mypy
- **Test Framework (TS)** - Vitest
- **Test Framework (Python)** - pytest
- **Check Command (TS)** - `npm run check`
- **Check Command (Python)** - `cd pipeline && python -m pytest && mypy .`

---

## Document History

- **v1.0** - 2026-02-10 - emhar - Initial standards from architecture.md
