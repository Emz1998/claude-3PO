---
name: specs
description: Creates project documentation (product-vision, product-brief, architecture, coding-standards, definition-of-done, decisions). Use when user mentions "Create Specs", "Create Architecture", "Create Product Vision", or needs foundational project documentation.
disable-model-invocation: true
hooks:
  PreToolUse:
    - matcher: "AskUserQuestion"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/skills/visionize/hooks/ask_user_question.py"
          timeout: 10
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/skills/visionize/hooks/pre_tool_use.py"
          timeout: 10
---

**Goal**: Create or update project documentation based on the dependency chain

## Dependency Chain

```
product-vision.md → architecture.md -> constitution.md
```

## Context

- **Action to be performed (create, update, delete)**: $0
- **Doc type (product-vision, product-brief, architecture, coding-standards, definition-of-done)**: $1
- **Instructions**: $2

## Instructions

- Each doc depends on its predecessors. `decisions.md` is standalone and can be updated at any time.
- If `Action to be performed` is `create` and `Doc type` is specified, then create the specified doc while respecting the dependency chain. If dependency is not met yet, exit and inform the user to create the missing docs first.
- If `Action to be performed` is `create` but `Doc type` is not specified, then create all docs in the dependency chain.
- If `Action to be performed` is `update` or `delete` but `Doc type` is not specified, ask the user to specify the doc type to update or delete.
- If No `Action to be performed` is specified and no `Doc type` is specified and no `Instructions` are provided, default to `create` and create all docs in the dependency chain.

## Workflow

1. Identify which doc type the user wants to create or update
2. Verify all dependencies exist (read predecessor docs in the chain)
3. Read `project/docs/executive/product-vision.md` for project context
4. Read `project/docs/executive/business-plan.md` for business plan context
5. Read predecessor docs for context relevant to the target doc
6. Choose template from `.claude/skills/specs-creator/templates/` depending on the `Doc type`
7. Generate doc with project-specific content
8. Save to the correct path in `project/docs/` (See `Output Path` section for details)
9. Report completion with file path and next steps in the dependency chain

## Constraints

- NEVER create a doc if its dependency doesn't exist yet
- NEVER overwrite existing docs without user approval
- NEVER assume requirements - ask for clarification
- KEEP docs aligned with the project's constitution and existing decisions

## Acceptance Criteria

- [ ] Doc contains all required sections from its template
- [ ] Saved to the correct path under `project/docs/`
- [ ] Content is consistent with predecessor docs in the chain
- [ ] Completion report includes: file path, doc type, next steps

## References

- **Product Vision:** `.claude/project/docs/executive/product-vision.md`
- **Business Plan:** `.claude/project/docs/executive/business-plan.md`
- **Templates:** `.claude/skills/specs-creator/templates/`

## Output Path

- **Product Brief:** `project/docs/product/product-brief.md`
- **Architecture:** `project/docs/architecture.md/architecture.md`
- **Coding Standards:** `project/docs/architecture.md/coding-standards.md`
- **Definition of Done:** `project/docs/governance/definition-of-done.md`
- **Decisions:** `project/docs/architecture.md/decisions.md`

## Available Doc Types

| Type               | Path                                               | Template                          | Depends On            |
| ------------------ | -------------------------------------------------- | --------------------------------- | --------------------- |
| Product Vision     | `project/docs/executive/product-vision.md`         | `templates/product-vision.md`     | `app-vision.md`       |
| Product Brief      | `project/docs/product/product-brief.md`            | `templates/product-brief.md`      | `product-vision.md`   |
| Architecture       | `project/docs/architecture.md/architecture.md`     | `templates/architecture.md`       | `product-brief.md`    |
| Coding Standards   | `project/docs/architecture.md/coding-standards.md` | `templates/coding-standards.md`   | `architecture.md`     |
| Definition of Done | `project/docs/governance/definition-of-done.md`    | `templates/definition-of-done.md` | `coding-standards.md` |
| Decisions          | `project/docs/architecture.md/decisions.md`        | `templates/decisions.md`          | None                  |
