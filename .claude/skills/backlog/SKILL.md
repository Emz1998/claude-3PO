---
name: backlog
description: Creates and manages product backlog markdown files with epics, user stories, technical stories, bugs, and spikes. Use when creating backlogs, adding epics/stories/tasks, updating story status, or when user mentions backlog, sprint planning, project management, or task tracking.
---

**Goal**: Create and maintain a structured `backlog.md` file at `project/workflow/backlog.md` using the template at `template/backlog.md`.

## Instructions

- Read project specs for context before creating or modifying the backlog
- **Hierarchy**: Epics (EP-NNN) contain stories (US-NNN, TS-NNN, BG-NNN, SK-NNN). Tasks (T-NNN) are created at sprint level, not in the backlog
- All IDs are global and sequential within their prefix
- Use priority levels: Must have, Should have, Nice to have
- Spikes reference which story they unblock
- Bugs reference the story they were found in (if known)
- A story can only belong to one epic
- Stories that don't fit an epic go in **Tech Debt / Infrastructure** or **Bug Backlog** sections

## Workflow

1. Read project specs for context:
   - **Product Vision**: `.claude/project/docs/product-vision.md`
   - **Architecture**: `.claude/project/docs/architecture/architecture.md`
   - **Constitution**: `.claude/project/docs/governance/constitution.md`

2. Read the backlog template: [template/backlog.md](template/backlog.md)

3. Check if `backlog.md` exists at `project/workflow/backlog.md`. If not, create it from the template.

4. Create or update the backlog following the template structure:
   - Fill the **Epics Overview** table with all epics and their priorities
   - Fill **Epic Details** sections with stories for each epic
   - Populate **Tech Debt / Infrastructure** and **Bug Backlog** as needed
   - Move completed stories to the **Completed** table

5. Provide summary report to the user

## Rules

- Most stories should be independent per INVEST principles
- Avoid dependencies between stories as much as possible
- Do not add task-level detail to the backlog; that belongs in sprint planning
- Must have bugs take priority over Should have stories in the next sprint
- Reprioritize at every sprint close based on Scrum Master recommendations
- Stories use their type-specific format (US/TS/BG/SK) matching sprint.md conventions

## Acceptance Criteria

- Backlog follows the exact structure from `template/backlog.md`
- All IDs follow correct patterns (EP-NNN, US-NNN, TS-NNN, BG-NNN, SK-NNN)
- Each epic has a description, priority, and status
- Stories use the correct format: "As a [user], I want [what] so that [why]"
- Priority legend, status values, and ID conventions match the template
- Epics Overview table accurately reflects current counts and statuses
- File written to correct path: `project/workflow/backlog.md`
