---
name: dry-run
description: Dry run a command to see what it will do
argument-hint: <command>
model: opus
---

## Instructions

- Do not implement any changes.
- No work should be done.
- /log:task only accepts input in the format of `<task-id> <status>` where task-id follows the format of `T001`, `T002`, `T003`, etc. and status is one of the following: `completed`, `blocked`
- **Important**: Do not instruct `subagents` to perform any work or changes
- **Important**: Do not give any tasks to the subagents.
- Tell the subagents that this is a dry run and to exit right away.

## Workflow

1. Create a .claude/hooks/cache.json file if it doesn't exist.
2. Add and set `build_skill_active` to `True` in .claude/hooks/cache.json
3. Run this workflow sequentially using the `Skill` tool: `/roadmap:query` → `/explore` → `/discuss` → `/plan` → `/prototype` → `/code` -> `/log:task`

## Prohibited Tasks

- Instructing `subagents` to perform any work or changes
- You perform any work or changes
