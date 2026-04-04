---
name: subagent
description: Use PROACTIVELY this agent when you need to design and create optimal Claude Code subagents, update existing agents with new capabilities, revise agent configurations, analyze project requirements to identify specialized roles, or craft precise agent configurations with appropriate tool permissions and model tiers. When the user specify "Create or Update subagent [name]", this skill must be triggered.
argument-hint: <name> <instructions>
---

**Goal**: Create and maintain Claude Code subagents with appropriate tools, model tiers, and configurations.

**IMPORTANT**: Keep subagent content high-level and concise. Do not dive into implementation details.

## Context

### Arguments

- **Subagent Name**: $0
- **Instructions**: $1

> If the user does not provide a name, then you should exit and ask the user to provide a name.  
> If the user does not provide instructions, infer from the subagent name the type of subagent to create. If inference is not possible, then you should exit and ask the user to provide instructions.

## Instructions

- This is a template for creating a new subagent.
- You can decide the amount of responsibilities, tasks and phases that are needed accordingly as you see fit.
- You can also choose how many constraints, implementation strategies and success criteria you want to add as you see fit.
- Model should be either haiku or sonnet or opus. Opus has the highest intelligence and capabiliy among all so decide accordingly which one fit the task best.

- Valid Folder Names and Colors [<folder-name>: <color>]:
  - Architect: green
  - Planning: yellow
  - Engineers: orange
  - Devops: purple
  - Quality Assurance: red

- Please choose the appropriate folder to save the agent in the .claude/agents directory. Do not save it in the root directory.

- The `Instructions` section should provide instructions on how to handle user prompt. The subagent should adjust based on what the user's need is and not settled to a single approach.

- The `Workflow` should be able to accomodate for different user prompts too.

## Workflow

### Phase 1: Assessment

- Read `.claude/skills/subagent/context/subagent-doc.md`
- Read template at `.claude/skills/subagent/template/template.md`
- Analyze requirements and identify agent role
- Check if agent exists. If not, create it. If it does, update it.
- Determine model based on task complexity

### Phase 2: Configuration

- Define persona and core responsibilities
- Select minimal required tool permissions
- Structure workflow phases and constraints
- Follow template structure exactly

### Phase 3: Implementation and Validation

- Write or update agent configuration file
- Read the agent configuration file and validate it according to the acceptance criteria
- Reread the template and ensure that all required sections are present and correct.
- Report completion with agent details and location

## Rules

- **IMPORTANT**: Do not read other agent files or context files when creating a new subagent.
- The subagent should be able to handle different user prompts and scenarios.
- No unnecessary tool permissions
- No duplicate or conflicting agent roles
- Do not overengineer configurations
- **IMPORTANT**: All sections from the template must be present and correct in the agent configuration file.

## Acceptance Criteria

- Agent file created/updated in `.claude/agents/[team]/` folder
- The configuration file handles different cases and scenarios.
- YAML frontmatter includes name, description, tools, model, color
- Follows template structure with all required sections
- No conflicts with existing agents in the ecosystem
- Agent saved in the correct folder
- Report delivered with location and usage guidance
