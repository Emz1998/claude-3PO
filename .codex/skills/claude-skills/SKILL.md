---
name: claude-skills
description: Creates and maintains Agent Skills with effective triggers and progressive disclosure. Use when user requests to create a skill, generate a SKILL.md, build custom capabilities, or mentions "create skill", "new skill", or "skill configuration".
argument-hint: <action-to-be-performed> <instructions>
---

**Goal**: Create well-structured Agent Skills following best practices for discoverability, conciseness, and progressive disclosure.

**IMPORTANT**: Skills configuration should be concise and high-level. Only include context Claude does not already know.

## Context

- $0 = <action-to-be-performed>
- $1 = <instructions> or <skill-name>
- $2 = <instructions> (conditionally required)

## Instructions

### If `Action to be performed` is `create`

> If `skill-name` or `instructions` are not provided, then you should exit and ask the user to provide a skill name and instructions.

- Create a new skill in the `.claude/skills/` directory with the name of the `skill-name`
- Configure the skill with the `instructions` provided by the user.
- The `SKILL.md` file should be created using the template from `.claude/skills/claude-skills/templates/template.md`
- Add resources(reference files, scripts, etc.) alongside the SKILL.md file only if necessary. Use folder to organize resources.
- Save the `SKILL.md` file to the `.claude/skills/[skill-name]/SKILL.md` file.

### If `Action to be performed` is `update`

> If `skill-name` or `instructions` are not provided, then you should exit and ask the user to provide a skill name and instructions.

- Update the existing skill in the `.claude/skills/` directory with the name of the `skill-name`
- Configure the skill with the `instructions` provided by the user.
- The `SKILL.md` file should be updated using the template from `.claude/skills/claude-skills/templates/template.md`

### If `Action to be performed` is `delete`

> If `skill-name` is not provided, then you should exit and ask the user to provide a skill name.

- Delete the existing skill in the `.claude/skills/` directory with the name of the `skill-name`
- Delete the `SKILL.md` file from the `.claude/skills/[skill-name]/SKILL.md` file.

### If `Action to be performed` is `list`

- List all existing skills in the `.claude/skills/` directory.

> **Note**: Supporting files should be store within the skill folder. E.g. `.claude/skills/[skill-folder-name]/[supporting file name or folder]`
> **Note**: The folder name and the skill name should be the same.

## Workflow

1. Analyze the arguments provided by the user.
2. Implement the conditional instructions based on the arguments provided by the user.
3. Read references: `skills-docs.md` and `best-practices.md` in `.claude/skills/claude-skills/references/`
4. Read the template from `.claude/skills/claude-skills/templates/template.md`
5. Implement the task based on the instructions above.
6. Validate the `SKILL.md` file against the acceptance criteria and the template.
7. Report completion with skill details and location.

## Rules

- Only add context Claude doesn't already know
- Keep references one level deep from SKILL.md
- Provide one default approach, avoid offering multiple options
- `Update` task should only focus on updating skills and should not touch any other files or folders.
- Match freedom level to task fragility (high freedom for flexible tasks, low for critical operations)

## Acceptance Criteria

- Skill saved to `.claude/skills/[skill-name]/SKILL.md`
- Name valid (max 64 chars, lowercase letters/numbers/hyphens only)
- Description valid (max 1024 chars, third person, no "I" or "you")
- Description includes what skill does AND when to use it
- SKILL.md body under 500 lines
- Consistent terminology throughout
- No duplicate or conflicting skills exist
- No time-sensitive information included
- Name defined using gerund form (e.g., `processing-pdfs`, `analyzing-data`)
- Skill's structure is consistent with the template provided.
