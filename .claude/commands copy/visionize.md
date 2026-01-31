---
name: discuss
description: Interactive discussion session for implementation strategy and decision-making using AskUserQuestion tool
allowed-tools: AskUserQuestion, Read, Glob, Grep, Write
argument-hint: <topic-or-task-to-discuss>
model: sonnet
---

**Goal**: Facilitate interactive discussion sessions to explore implementation strategies and make decisions for the current task

## Workflow

### Phase 1: Context Gathering

- Use `AskUserQuestion` to understand the topic or task to discuss
- If milestone context needed, identify the current milestone from user input
- Gather any additional context about the project state or constraints

### Phase 2: Discussion Loop

- Use `AskUserQuestion` to present implementation options and trade-offs
- Ask clarifying questions to understand user preferences
- Propose strategies and gather feedback iteratively
- Continue discussion until user indicates completion

### Phase 3: Completion Check

- Use `AskUserQuestion` to confirm if discussion is complete
- If not done, return to Phase 2 for more exploration
- If done, proceed to Phase 4

### Phase 4: Decision Documentation

- Use `AskUserQuestion` to confirm creating the decision file
- Create `project/v0.1.0/milestones/[MS-NNN]_[Milestone-Description]/decisions/decision_[date]_[session-id].md`
- Document all decisions made during the session

## Constraints

- **NEVER** output text without using `AskUserQuestion` tool for discussion
- **NEVER** use other output styles aside from `AskUserQuestion` during discussion
- **NEVER** skip the completion confirmation step
- **NEVER** create decision file without user approval
- **DO NOT** make assumptions without validating with user
- **DO NOT** end session without documenting decisions

## Decision File Format

```markdown
# Decision Record: [Topic]

**Date**: [YYYY-MM-DD]
**Session ID**: [unique-id]
**Milestone**: [MS-NNN] [Milestone Description]

## Context

[Brief description of the discussion context]

## Decisions Made

1. [Decision 1]
2. [Decision 2]
3. [Decision 3]

## Rationale

[Key reasoning behind decisions]

## Next Steps

[Action items resulting from this discussion]
```

## Acceptance Criteria

- All interactions use `AskUserQuestion` tool
- User confirms discussion is complete before documenting
- Decision file created with all discussed decisions
- File saved to correct milestone directory
