---
name: create-release-plan
description: Creates and manages release-plan.json files with releases, epics, features, user stories, and tasks. Use when creating release plans, adding epics/features/stories/tasks, updating status, or when user mentions release planning, project management, or task tracking.
---

**Goal**: Create and maintain structured `release-plan.json` files in `project/release-plans/release-plan.json`.

## Instructions

- Read specs (app-vision.md, PRD.md, tech-specs.md, ui-ux.md) for context before creating or modifying release plans.
- **Hierarchy**: releases > epics > features > user_stories > tasks
- A single release-plan.json contains multiple releases (versions), each with its own epics.
- Determine if a feature needs TDD based on complexity. Set `tdd: true` if applicable.
- Break large features into smaller features and user stories.
- Epics use `requirements` with `functional` (FR) and `non_functional` (NFR) items.
- User stories use `story` field (not `title`) and `context` field (not `description`).
- Future releases can have empty `epics` arrays as placeholders.

## Workflow

1. Read the following specs files:
   - **PRD**: `project/product/PRD.md`
   - **Tech Specs**: `project/{version}/specs/tech-specs.md`
   - **UI/UX Specs**: `project/{version}/specs/ui-ux.md`
   - **App Vision**: `project/executive/app-vision.md`

2. Read the schema structure file:
   - **Schema Structure**: `.claude/skills/release-plan/references/schema-structure.md`
   - **Sample Schema**: `.claude/skills/release-plan/references/sample-schema.json`

3. Check if `release-plan.json` exists at `project/release-plans/release-plan.json`. If not, create it.
4. Create or update the `release-plan.json` based on the schema structure and sample schema.
5. Validate using: `uv run .claude/skills/release-plan/scripts/validate_release_plan.py -i project/release-plans/release-plan.json`
6. Provide summary report to the user.

## Acceptance Criteria

- `release-plan.json` follows exact structure from schema-structure.md
- All IDs follow correct patterns (`EPIC-NNN`, `FEAT-NNN`, `US-NNN`, `TNNN`, `SC-NNN`, `AC-NNN`, `FR-NNN`, `NFR-NNN`)
- Task dependencies reference valid `TNNN` IDs
- Epic requirements use `functional` (FR) and `non_functional` (NFR) arrays
- Features use `tdd` boolean field for test strategy
- User stories use `story` and `context` fields
- Multiple releases supported in a single file
- File written to correct path: `project/release-plans/release-plan.json`
