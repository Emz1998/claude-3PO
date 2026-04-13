---
name: install-deps
description: Phase 5 — Install dependencies listed in the plan's ## Dependencies section.
argument-hint: <optional-additional-context>
model: sonnet
---

**Phase 5: Install Dependencies**

## Workflow

### Step 1: Read Dependencies

Read the plan's `## Dependencies` section from `.claude/plans/latest-plan.md`.
The guardrail has already extracted the package names into state.

### Step 2: Write Package Manager File

Write dependencies to the appropriate package manager file:
- Python: `requirements.txt` or `pyproject.toml`
- Node.js: `package.json`
- Go: `go.mod`
- Rust: `Cargo.toml`
- Ruby: `Gemfile`

Only package manager files are allowed — the guardrail blocks all other writes.

### Step 3: Run Install Command

Run the install command for the project's package manager:
- `pip install -r requirements.txt`
- `npm install`
- `yarn install`
- `go mod tidy`
- `cargo add`
- `gem install`

Only install commands are allowed — the guardrail blocks all other Bash commands.

### Step 4: Verify Installation

The guardrail automatically marks the phase complete when an install command runs successfully.

## Constraints

- Only package manager files can be written (e.g. `package.json`, `requirements.txt`)
- Only install commands are allowed via Bash
- If there are no dependencies, skip this phase
