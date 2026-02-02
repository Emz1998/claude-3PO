---
name: plan
description: Create implementation plan by delegating to strategic-planner and consulting-expert agents
allowed-tools: Read, Write, Glob, Grep, Task
argument-hint: <instructions>
model: sonnet
---

**Goal**: Create a detailed implementation plan based on research findings

## Workflow

1. Invoke @agent-planner subagent to create the implementation plan
2. Invoke @agent-consultant subagent to review and consult on the plan
3. Report plan summary to user

## Subagent Prompts

### Step 1: Strategic Planner

Delegate to @agent-planner subagent with this prompt:

```
Create implementation plan for: $2 - $3
Plan type: $1

Using the validated research findings, create:
1. Executive summary
2. Implementation phases with task breakdowns
3. Risk mitigation strategies
4. Success criteria and acceptance tests
5. Dependencies and constraints

Output: Create project/[milestone]/plans/plan_[session]_[date].md
```

### Step 2: Consulting Expert

Delegate to @agent-consultant subagent with this prompt:

```
Review the implementation plan at:
project/[milestone]/plans/plan_[session]_[date].md

Evaluate:
1. Technical feasibility
2. Risk assessment accuracy
3. Resource allocation
4. Alternative approaches considered
5. Potential blind spots

Update frontmatter with: consulted_by: consulting-expert
Provide actionable feedback and recommendations.
```
