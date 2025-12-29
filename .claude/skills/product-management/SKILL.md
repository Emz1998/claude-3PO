---
name: generating-product-prds
description: Generates Product Requirements Documents (PRDs) in JSON format following the PRD.json schema. Use when creating new products, defining features, writing user stories, or when user mentions PRD, product requirements, or product definition.
---

**Goal**: Generate structured PRD JSON files that define products, versions, features, user stories, and requirements.

## Instructions

- All generated JSON must conform to the schema in `.claude/skills/product-management/references/schema-structure.md`.
- **Important**: `v0.1.0` is the MVP version.
- Ensure the number of version are at least 10 and span from v0.1.0 to v1.0.0. To achieve this, break down big version to smaller versions.
- Breakdown big feature to smaller features.
- Use the app vision to generate the PRD.
- Ensure Success Criteria (SC) and Acceptance Criteria (AC) are specific enough and broken down into multiple smaller criteria if needed for clarity.
- **Important**: The schema.json is just a sample structure. Ignore the content and just focus on the structure.

## Workflow

1. Read app vision: `project/executive/app-vision.md` (primary context source)
2. Read schema: `.claude/skills/product-management/references/schema-structure.md`
3. Reference sample structure: `.claude/skills/product-management/references/sample-schema.json`
4. Generate `PRD.json` at `project/product/PRD.json`
5. Validate JSON structure against schema using the by running `python .claude/skills/product-management/scripts/validate_prd.py -i project/product/PRD.json`
6. Use the script `prd_to_markdown.py` to generate `PRD.md` at `project/product/PRD.md` by running `python .claude/skills/product-management/scripts/prd_to_markdown.py`

## Acceptance Criteria

- JSON saved to `project/product/PRD.json`
- Markdown saved to `project/product/PRD.md`
- All required fields present per schema
- Valid JSON syntax
- IDs follow naming conventions
- Metadata includes current date and author

## Special Considerations

### ID Conventions

| Prefix | Entity                     | Example   |
| ------ | -------------------------- | --------- |
| `F`    | Feature                    | `F001`    |
| `US`   | User Story                 | `US-001`  |
| `AC`   | Acceptance Criteria        | `AC-001`  |
| `FR`   | Functional Requirement     | `FR-001`  |
| `NFR`  | Non-Functional Requirement | `NFR-001` |
| `D`    | Dependency                 | `D001`    |
| `R`    | Risk                       | `R001`    |
| `SC`   | Success Criteria           | `SC-001`  |
