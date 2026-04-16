---
name: sprint
description: Creates and manages sprint backlog markdown files with user stories, technical stories, bugs, spikes, and tasks. Use when creating sprints, planning sprint work, adding stories/tasks to a sprint, updating sprint status, or when user mentions sprint, sprint planning, or sprint backlog.
hooks:
  PreToolUse:
    - hooks:
        - type: command
          command: '${CLAUDE_PLUGIN_ROOT}/sprint/hooks/pre_tool_use.py'
---

**Goal**: Create and maintain a structured sprint backlog at `.claude/projects/sprint.md` using the template at [template/sprint.md](template/sprint.md).

## Instructions

- Read the backlog at `.claude/projects/backlog.md` and project specs before creating a sprint
- Pull stories from the backlog into the sprint based on priority and capacity
- **Story types**: User Story (US-NNN), Technical Story (TS-NNN), Bug (BG-NNN), Spike (SK-NNN)
- **Task complexity**: S=1, M=2, L=3 points. Story points = sum of task complexities
- Create a `User Story title` based on the user story description (As a `[user role]`, I want `[capability]` so that `[benefit]`.). It must be short and concise.
- Tasks have acceptance criteria, dependency tracking, QA loops (0/3), and Code Review loops (0/2)
- Spikes are timeboxed, produce decisions (not code), and bypass the QA/Code Review pipeline
- Must-have bugs take priority over Should-have stories
- Update the Sprint Overview table daily with current statuses

## Workflow

1. Read project context:
   - **Backlog**: `.claude/projects/backlog.md`

2. Read the sprint template: [template/sprint.md](template/sprint.md)

3. Check if `sprint.md` exists at `.claude/projects/sprint.md`. If not, create it from the template.

4. Create or update the sprint:
   - Fill sprint metadata (project, number, goal, dates, capacity)
   - Pull stories from backlog based on priority and capacity
   - Break stories into tasks with acceptance criteria and complexity estimates
   - Set task dependencies and identify blocked items
   - Populate the Sprint Overview table
   - Calculate total story points

5. Validate against the acceptance criteria and template structure.

6. Provide summary report to the user

## Rules

- Most stories should be independent per INVEST principles
- Avoid dependencies between stories as much as possible
- IDs are global and sequential within their prefix (consistent with backlog)
- Each task must have at least one acceptance criterion
- Spike points are S or M only (never L)
- Task statuses: Todo, In Progress, In Review, Done, Blocked
- Story statuses: Todo, In Progress, Done, Partial
- Do not exceed sprint capacity
- Stories use their type-specific format matching the template conventions
- User Story title is not the same as the user story description (As a `[user role]`, I want `[capability]` so that `[benefit]`.). It must be short and concise.
- If Stories do not have an epic, leave the `Epic` column as `-`
- If Tasks do not have a dependency, leave the `Depends on` column as `-`

## Acceptance Criteria

- Sprint follows the exact structure from `template/sprint.md`
- All IDs follow correct patterns (US-NNN, TS-NNN, BG-NNN, SK-NNN, TASK-NNN)
- Each story has acceptance criteria at both story and task level
- Sprint Overview table reflects all stories with correct points and statuses
- Total points calculated and within sprint capacity
- Task dependencies are explicitly declared
- File written to correct path: `.claude/projects/sprint.md`
