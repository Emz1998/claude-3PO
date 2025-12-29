---
name: project-management
description: Creates and manages project roadmap.json files with phases, milestones, and tasks. Use when creating roadmaps, adding phases/milestones/tasks, updating status, or when user mentions roadmap management, release planning, or project phases.
---

**Goal**: Create and maintain structured roadmap.json files in `project/{version}/release-plan/roadmap.json` that track project phases, milestones, and tasks.

## Instructions

- Read specs (app-vision.md, PRD.md, tech-specs.md, ui-ux.md) for context before creating or adding to roadmap.
- **Important**: Phases run SEQUENTIALLY. Milestones within a phase run in PARALLEL. If a milestone must run sequentially, place it in its own single-milestone phase.
- Tasks are owned by subagents in `.claude/agents/engineers/`. The main role of the main agent is to orchestrate the subagents and ensure the tasks are completed in the correct order.
- Determine if a task need to use `TDD` or `TA` based on complexity of the task. If a task does not require testing, leave it blank.
- Determine if a milestone need to use MCP servers. If a milestone does not require MCP, leave it blank.
- Always breakdown big feature to smaller features.
- Make sure Success Criteria (SC) and Acceptance Criteria (AC) are broken down into multiple smaller criteria if needed.

## Workflow

1. Read the following specs files:

   - **PRD**: `project/product/PRD.md`
   - **Tech Specs**: `project/{version}/specs/tech-specs.md`
   - **UI/UX Specs**: `project/{version}/specs/ui-ux.md`
   - **App Vision**: `project/executive/app-vision.md`

2. Read the schema structure files:

   - **Schema Structure**: `.claude/skills/project-management/references/schema-structure.md`
   - **Sample Schema**: `.claude/skills/project-management/references/sample-schema.json`

3. Read the MCP servers list: `.claude/skills/project-management/references/mcp-servers.txt`
4. Read the task owners list: `.claude/agents/engineers/`

5. Check if roadmap.json exists in the target path. If it does not exist, create it.
6. Create the roadmap.json file based on the schema structure and sample schema.
7. Validate the roadmap.json schema using the script `validate_roadmap.py`
8. Provide summary report to the user.

## Acceptance Criteria

- Roadmap.json follows exact structure from schema.json
- All IDs follow correct patterns (PH-NNN, MS-NNN, TNNN, SC-NNN, AC-NNN)
- Feature references in milestones match PRD feature IDs
- Success criteria use `id`, `description`, and `status` fields
- Acceptance criteria use `id`, `description`, and `status` fields
- Task `parallel` field is set correctly based on dependencies
- Summary section accurately reflects current counts
- Current section contains active phase, milestone, and task IDs
- metadata.last_updated is current ISO 8601 datetime
- Task owners are validated against .claude/agents/engineers/
- File written to correct path: project/{version}/release-plan/roadmap.json
